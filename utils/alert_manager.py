"""
Singleton manager for handling application-wide alerts.

This module provides a centralized way to show and manage alerts throughout the application.
Alerts can contain a main message and optional additional information with custom colors.
"""
from typing import Optional, List, Tuple, Any
from utils.theme import Theme

class AlertManager:
    """
    Singleton manager for handling application-wide alerts.
    
    This class provides methods to show, hide, and manage alert dialogs from any part
    of the application without creating circular dependencies.
    
    Attributes:
        _instance: The singleton instance of AlertManager
        showing_alert (bool): Whether an alert is currently being shown
        alert_message (str): The current alert's main message
        alert_additional_info (List[Tuple[str, Tuple[int, int, int, int]]]): Additional info with colors
        _app_instance: Reference to the main application instance
    """
    _instance = None
    
    def __init__(self) -> None:
        """Initialize the AlertManager. Should not be called directly - use get_instance()."""
        if AlertManager._instance is not None:
            raise RuntimeError("AlertManager is a singleton - use get_instance() instead")
        
        self.showing_alert: bool = False
        self.alert_message: str = ""
        self.alert_additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None
        self._app_instance = None
    
    @classmethod
    def get_instance(cls) -> 'AlertManager':
        """Get the singleton instance of AlertManager.
        
        Returns:
            AlertManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = AlertManager()
        return cls._instance
    
    def set_app(self, app_instance: Any) -> None:
        """Set the application instance for the alert manager.
        
        Args:
            app_instance: The main application instance
        """
        self._app_instance = app_instance
    
    def show_alert(self, 
                  message: str, 
                  additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None) -> None:
        """Show an alert dialog with the given message and optional additional information.
        
        Args:
            message: The main message to display in the alert
            additional_info: Optional list of tuples containing (text, color) for additional lines
                           Color should be an RGBA tuple (r, g, b, a)
        
        Example:
            ```python
            alert_manager = AlertManager.get_instance()
            alert_manager.show_alert(
                "Download Failed",
                [
                    ("Game Name", Theme.TEXT_PRIMARY),
                    ("Connection error occurred", Theme.ERROR)
                ]
            )
            ```
        """
        self.showing_alert = True
        self.alert_message = message
        self.alert_additional_info = additional_info
    
    def show_error(self, message: str, details: Optional[str] = None) -> None:
        """Show an error alert with the given message.
        
        Args:
            message: The main error message
            details: Optional error details
        """
        additional_info = [(details, Theme.ERROR)] if details else None
        self.show_alert(message, additional_info)
    
    def show_success(self, message: str, details: Optional[str] = None) -> None:
        """Show a success alert with the given message.
        
        Args:
            message: The main success message
            details: Optional success details
        """
        additional_info = [(details, Theme.SUCCESS)] if details else None
        self.show_alert(message, additional_info)
    
    def show_warning(self, message: str, details: Optional[str] = None) -> None:
        """Show a warning alert with the given message.
        
        Args:
            message: The main warning message
            details: Optional warning details
        """
        additional_info = [(details, Theme.WARNING)] if details else None
        self.show_alert(message, additional_info)
    
    def show_info(self, message: str, details: Optional[str] = None) -> None:
        """Show an info alert with the given message.
        
        Args:
            message: The main info message
            details: Optional info details
        """
        additional_info = [(details, Theme.INFO)] if details else None
        self.show_alert(message, additional_info)
    
    def hide_alert(self) -> None:
        """Hide the currently showing alert."""
        self.showing_alert = False
        self.alert_message = ""
        self.alert_additional_info = None
    
    def is_showing(self) -> bool:
        """Check if an alert is currently showing.
        
        Returns:
            bool: True if an alert is showing, False otherwise
        """
        return self.showing_alert
    
    def get_message(self) -> str:
        """Get the current alert message.
        
        Returns:
            str: The current alert message
        """
        return self.alert_message
    
    def get_additional_info(self) -> Optional[List[Tuple[str, Tuple[int, int, int, int]]]]:
        """Get the current alert's additional information.
        
        Returns:
            Optional[List[Tuple[str, Tuple[int, int, int, int]]]]: List of (text, color) tuples
                                                                   or None if no additional info
        """
        return self.alert_additional_info 