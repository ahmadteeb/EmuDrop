import subprocess

def check_internet_connection():
    """
    Check internet connectivity by pinging 8.8.8.8
    Returns True if connection is available, False otherwise
    """
    try:
        subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run(infoScreen):
    infoScreen.show_message(message="Checking internet connection...")
    connection = check_internet_connection()
    if connection:
        infoScreen.show_message(message="Internet connection detected.", duration=0.25)
    else:
        infoScreen.show_message(message="No internet connection. Press B to exit.", wait_for_button=1)
    
    return connection
