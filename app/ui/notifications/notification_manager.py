import logging
from typing import Optional
from pathlib import Path
import threading
from queue import Queue
import time as time_module
import customtkinter as ctk
from PIL import Image
from app.config.settings import NOTIFICATIONS, BUSINESS_HOURS, APP_NAME, DEFAULT_APP_ICON

logger = logging.getLogger(__name__)

class TrayNotifier:
    """Gerencia notificações usando plyer para notificações do sistema"""
    def __init__(self):
        self.enabled = NOTIFICATIONS['enabled'] and NOTIFICATIONS['tray']['enabled']
        self.queue = Queue()
        self.worker_thread = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            self._start_worker()
    
    def _start_worker(self):
        """Inicia thread de processamento de notificações"""
        self.worker_thread = threading.Thread(
            target=self._process_notifications,
            daemon=True,
            name="Notification-Worker"
        )
        self.worker_thread.start()
        logger.debug("Worker de notificações iniciado")
    
    def notify(self, title: str, message: str, level: str = 'info', timeout: Optional[int] = None, icon: Optional[str] = None):
        """Envia uma notificação"""
        if not self.enabled:
            return
            
        config = NOTIFICATIONS['tray']['levels'].get(level, {})
        if not config.get('enabled', True):
            return
            
        notification = {
            'title': title,
            'message': message,
            'level': level,
            'timeout': timeout or config.get('timeout', NOTIFICATIONS['tray']['default_timeout']),
            'icon': icon or config.get('icon', DEFAULT_APP_ICON)
        }
        
        self.queue.put(notification)
    
    def _process_notifications(self):
        """Processa a fila de notificações"""
        try:
            from plyer import notification
        except ImportError:
            logger.error("plyer não está instalado. Notificações do sistema não funcionarão.")
            return

        while not self._stop_event.is_set():
            try:
                if not self.queue.empty():
                    notif = self.queue.get()
                    notification.notify(
                        title=notif['title'],
                        message=notif['message'],
                        app_icon=str(notif['icon']) if notif['icon'] else None,
                        timeout=notif['timeout']
                    )
                time_module.sleep(0.1)
            except Exception as e:
                logger.error(f"Erro ao processar notificação: {e}")
    
    def shutdown(self):
        """Finaliza o worker de notificações"""
        self._stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        logger.debug("Worker de notificações finalizado")


class MessageBoxManager:
    """Gerencia caixas de diálogo usando CTk"""
    def __init__(self):
        self.enabled = NOTIFICATIONS['enabled'] and NOTIFICATIONS['messagebox']['enabled']
        
    def show_message(self, title: str, message: str, level: str = 'info') -> None:
        """Exibe uma mensagem"""
        if not self.enabled:
            return
            
        config = NOTIFICATIONS['messagebox']['levels'].get(level, {})
        if not config.get('enabled', True):
            return
            
        dialog = ctk.CTkInputDialog(
            text=message,
            title=title
        )
        dialog.get_input()  # Mostra o diálogo e espera o OK
    
    def ask_question(self, title: str, message: str) -> bool:
        """Exibe uma pergunta e retorna True para Sim e False para Não"""
        if not self.enabled:
            return False
            
        config = NOTIFICATIONS['messagebox']['levels'].get('question', {})
        if not config.get('enabled', True):
            return False
            
        dialog = ctk.CTkInputDialog(
            text=message,
            title=title
        )
        result = dialog.get_input()
        return result is not None  # None significa que cancelou/fechou


class BusinessHoursNotifier:
    """Gerencia notificações de horário comercial"""
    def __init__(self):
        self.enabled = NOTIFICATIONS['enabled']
        self._setup_messages()
        self.timers = {}
    
    def _setup_messages(self):
        """Configura mensagens padrão para diferentes tipos de notificação"""
        self.messages = {
            'start': {
                'title': f'Início do Expediente - {APP_NAME}',
                'message': 'Bom dia! Hora de começar o trabalho.',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['start']['icon']
            },
            'interval_start': {
                'title': 'Hora do Almoço',
                'message': 'Bom almoço! Aproveite seu intervalo.',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['interval_start']['icon']
            },
            'interval_end': {
                'title': 'Retorno do Almoço',
                'message': 'Hora de voltar ao trabalho!',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['interval_end']['icon']
            },
            'end': {
                'title': 'Fim do Expediente',
                'message': 'Bom descanso! O expediente está encerrado.',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['end']['icon']
            },
            'coffee': {
                'title': 'Hora do Café',
                'message': 'Que tal uma pausa para um café? ☕',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['coffee']['icon']
            },
            'water': {
                'title': 'Hidratação',
                'message': 'Momento de beber água! 💧\nMantenha-se hidratado!',
                'level': 'info',
                'icon': NOTIFICATIONS['tray']['business_notifications']['water']['icon']
            }
        }
    
    def start_timers(self, master: ctk.CTk):
        """Inicia os timers usando a janela principal"""
        self.master = master
        for period, time_str in BUSINESS_HOURS.items():
            self._schedule_notification(period, time_str)
    
    def _schedule_notification(self, period: str, time_str: str):
        """Agenda uma notificação para um determinado período"""
        from datetime import datetime, timedelta
        
        if not hasattr(self, 'master'):
            logger.warning("Timers não podem ser agendados sem uma janela principal")
            return
            
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target <= now:
            target += timedelta(days=1)
        
        delay_ms = int((target - now).total_seconds() * 1000)
        
        # Usa o after do widget master ao invés do módulo ctk
        timer = self.master.after(delay_ms, lambda: self._show_period_notification(period))
        self.timers[period] = timer
        
        logger.debug(f"Timer configurado para {period} às {time_str} "
                    f"(próximo em {delay_ms/1000/60:.1f} minutos)")
    
    def _show_period_notification(self, period: str):
        """Exibe a notificação do período e reconfigura o timer"""
        if not self.enabled:
            return
            
        msg = self.messages.get(period)
        if msg:
            notifications.notify(
                title=msg['title'],
                message=msg['message'],
                level=msg['level'],
                timeout=10,
                icon=msg.get('icon', DEFAULT_APP_ICON)
            )
        
        # Reagenda para o próximo dia
        time_str = BUSINESS_HOURS[period]
        self._schedule_notification(period, time_str)
    
    def shutdown(self):
        """Cancela todos os timers"""
        for timer in self.timers.values():
            ctk.after_cancel(timer)

    def update_notification_state(self, notification_key: str, enabled: bool):
        """Atualiza o estado de uma notificação específica"""
        try:
            if not hasattr(self, 'master'):
                warning_msg = "Notificações não podem ser atualizadas sem uma janela principal"
                logger.warning(warning_msg)
                return

            status = "ativada" if enabled else "desativada"
            
            if notification_key in self.timers:
                if not enabled:
                    # Cancela o timer existente
                    self.master.after_cancel(self.timers[notification_key])
                    del self.timers[notification_key]
                    logger.info(f"Timer de notificação '{notification_key}' removido")
                else:
                    # Recria o timer
                    time_str = BUSINESS_HOURS.get(notification_key)
                    if time_str:
                        self._schedule_notification(notification_key, time_str)
                        logger.info(f"Timer de notificação '{notification_key}' recriado para {time_str}")
            elif enabled:
                # Se o timer não existe e queremos habilitar, criamos um novo
                time_str = BUSINESS_HOURS.get(notification_key)
                if time_str:
                    self._schedule_notification(notification_key, time_str)
                    logger.info(f"Novo timer de notificação '{notification_key}' criado para {time_str}")
            
            logger.info(f"Estado da notificação '{notification_key}' atualizado: {status}")
            
        except Exception as e:
            error_msg = f"Erro ao atualizar estado da notificação: {e}"
            logger.error(error_msg)
            notifications.notify(
                title="Erro no Sistema de Notificações",
                message=error_msg,
                level="error",
                timeout=5
            )


class NotificationManager:
    def __init__(self):
        self.tray = TrayNotifier()
        self.messagebox = MessageBoxManager()
        self.business_hours = BusinessHoursNotifier()
    
    def initialize(self, master: ctk.CTk):
        """Inicializa os timers com a janela principal"""
        self.business_hours.start_timers(master)
    
    def notify(self, title: str, message: str, level: str = 'info', timeout: Optional[int] = None, icon: Optional[str] = None):
        self.tray.notify(title, message, level, timeout, icon)
    
    def show_message(self, title: str, message: str, level: str = 'info'):
        self.messagebox.show_message(title, message, level)
    
    def show_error(self, title: str, message: str):
        """Exibe uma mensagem de erro"""
        self.notify(title, message, level='error')
        self.show_message(title, message, level='error')
    
    def show_warning(self, title: str, message: str):
        """Exibe uma mensagem de aviso"""
        self.notify(title, message, level='warning')
        self.show_message(title, message, level='warning')
    
    def show_success(self, title: str, message: str):
        """Exibe uma mensagem de sucesso"""
        self.notify(title, message, level='success')
        self.show_message(title, message, level='success')
    
    def ask_question(self, title: str, message: str) -> bool:
        return self.messagebox.ask_question(title, message)
    
    def shutdown(self):
        try:
            self.tray.shutdown()
            self.business_hours.shutdown()
            logger.debug("Gerenciadores finalizados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao finalizar gerenciadores: {e}")

    def __del__(self):
        self.shutdown()


# Instância global do gerenciador
notifications = NotificationManager()
