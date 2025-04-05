"""
Singleton manager for handling application-wide alerts.
"""
from typing import Optional, List, Tuple

class AlertManager:
    """
    Singleton manager for handling application-wide alerts.
    Allows showing alerts from any part of the application without circular dependencies.
    """
    _instance = None
    
    def __init__(self):
        if AlertManager._instance is not None:
            raise RuntimeError("AlertManager is a singleton - use get_instance() instead")
        
        self.showing_alert = False
        self.alert_message = ""
        self.alert_additional_info = None
        self._app_instance = None
        
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of AlertManager"""
        if cls._instance is None:
            cls._instance = AlertManager()
        return cls._instance
    
    def set_app(self, app_instance):
        """Set the application instance for the alert manager"""
        self._app_instance = app_instance
    
    def show_alert(self, message: str, additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None):
        """Show an alert dialog with the given message"""
        self.showing_alert = True
        self.alert_message = message
        self.alert_additional_info = additional_info
        
    def hide_alert(self):
        """Hide the currently showing alert"""
        self.showing_alert = False
        self.alert_message = ""
        self.alert_additional_info = None
        
    def is_showing(self) -> bool:
        """Check if an alert is currently showing"""
        return self.showing_alert
    
    def get_message(self) -> str:
        """Get the current alert message"""
        return self.alert_message
    
    def get_additional_info(self) -> Optional[List[Tuple[str, Tuple[int, int, int, int]]]]:
        """Get the current alert's additional information"""
        return self.alert_additional_info 