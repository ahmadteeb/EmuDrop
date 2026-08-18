from infoscreen import InfoScreen
import check_connection, app_ota, db_ota
import sys

if __name__ == '__main__':
    infoScreen = InfoScreen()
    connection = check_connection.run(infoScreen=infoScreen)
    if not connection:
        infoScreen.quit()
        sys.exit(1)
        
    app_ota.run(infoScreen=infoScreen)
    db_ota.run(infoScreen=infoScreen)
    infoScreen.quit()
    sys.exit(0)