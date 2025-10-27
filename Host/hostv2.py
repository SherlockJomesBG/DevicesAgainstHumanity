# Imports Libraries used in the program
import requests
from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import socket
import random
from PIL import Image, ImageTk
import sqlite3
import websockets
import asyncio
import qrcode
import threading
import os
import time
import re
import queue
import ssl
import warnings
import logging
import sys
import signal
import yt_dlp
import vlc

# Suppress SSL and asyncio warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Global flag for clean shutdown
shutdown_flag = False

# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    global shutdown_flag
    print("\n🛑 Ctrl+C detected - Exiting application...")
    shutdown_flag = True
    try:
        # Try to destroy the main window if it exists
        if 'welcomeWindow' in globals() and welcomeWindow:
            welcomeWindow.quit()
            welcomeWindow.destroy()
    except:
        pass
    os._exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# These libraries are used for the readAloud/readOut functionality
# GTTS is used to convert text to speech
# Pydub is used to convert the audio file to a .wav file
# Concurrent.futures is used to run the cleanup function in a separate thread
# Pygame is used to play the audio file
from gtts import gTTS
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import pygame

# Screeninfo is a python library that finds all the connected screens to the host and returns information about them
from screeninfo import get_monitors

# Collections is a python library that provides additional data structures to the built-in ones
from collections import Counter

#These are global values which have default values set at start. They are used in multiple functions so setting them here gives a clearer structure
global min
min = 0

# Audio streaming state management globals
_audio_player = None
_audio_media = None
_audio_state = "stopped"  # Can be: "stopped", "playing", "paused"
_audio_position_ms = 0
_audio_lock = threading.Lock()
_audio_stream_url = None

global max
max = 9

global pages
pages = 0

global currentPage
currentPage = 0

global answerCount
answerCount = None

global votes
votes = []

global gameCode
gameCode = ""

global clientID
clientID = ""

global users
users = []

global continueGame
continueGame = True

global questionCountdown
questionCountdown = 0

global votingCountdown
votingCountdown = 0

global selected
selected = 0

global selectedCardPacks
selectedCardPacks = []

global usedBlackCards
usedBlackCards = []

global usedWhiteCards
usedWhiteCards = []

global votingMethod
votingMethod = ''

global notificationActive
notificationActive = False

global maxPlayers
maxPlayers = 0

global numOfRounds
numOfRounds = 0

global roundNumber
roundNumber = 0

global currentQuestion
currentQuestion = ""

global countdownActive
countdownActive = False

global maxCardPackSize
maxCardPackSize = 0

global fontScale
fontScale = 0

global readCardsOut
readCardsOut = 'Off'

global readAloud
readAloud = 'Off'

global serverConnection
serverConnection = ''

global websocketConnected
websocketConnected = False

global animation
animation = False

global screenHeight
screenHeight = '1080'

global screenWidth
screenWidth = '1920'

global scaleWidth
scaleWidth = 1

global scaleHeight
scaleHeight = 1

global defaultMonitor
defaultMonitor = 0

global questionMode
questionMode = False

global playersAnswered
playersAnswered = 0

global answers
answers = []

global tempButtons
tempButtons = []

global tempButtonsBlack
tempButtonsBlack = []

global tempButtonsWhite
tempButtonsWhite = []

global cardButtons
cardButtons = []

global selectedUser
selectedUser = None

guiQueue = queue.Queue() #This starts a queue which is used to store messages to be displayed on the GUI

notificationQueue = [] #This is a queue that stores messages to be displayed as notifications

global notificationMonitorThread
notificationMonitorThread = None

global playback
playback = None

global executor
executor = ThreadPoolExecutor()

global playbackLock
playbackLock = threading.Lock()

global websocketSendLock
websocketSendLock = threading.Lock()

pygame.mixer.init()

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open("debug.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

# This function obtains the users settings from Settings.db and sets the global variables to the values stored in the database
def getSettings():
    global maxPlayers, votingMethod, numOfRounds, questionCountdown, votingCountdown, readCardsOut, maxCardPackSize, fontScale, readAloud

    settingsDB = sqlite3.connect("Settings.db")
    sDB = settingsDB.cursor()

    sDB.execute("SELECT maxPlayers, votingMethod, numOfRounds, questionCountdown, votingCountdown, readCardsOut, maxCardPackSize, fontScale, readAloud FROM settings")
    settings = sDB.fetchone()

    settingsDB.close()

    maxPlayers = int(settings[0])
    votingMethod = settings[1]
    if settings[2] == 0:
        numOfRounds = 'Unlimited'
    else:
        numOfRounds = str(settings[2])
    questionCountdown = int(settings[3])
    votingCountdown = int(settings[4])
    if settings[5] == 0:
        readCardsOut = 'Off'
    else:
        readCardsOut = 'On'
    if settings[6] == 0:
        maxCardPackSize = 'Unlimited'
    else:
        maxCardPackSize = str(settings[6])
    fontScale = int(settings[7])/100
    if settings[8] == 0:
        readAloud = 'Off'
    else:
        readAloud = 'On'

# This function creates the audio file for the message and then begins to play it
def readMessage(message: str):
    try:
        # Attempts to stop any audio that is currently playing
        stopPlayback()
        streamAudio(state='pause')
        
        # Unload any currently loaded audio to release file handles
        try:
            pygame.mixer.music.unload()
        except:
            pass
        
        # Add a small delay to ensure file is fully released
        time.sleep(0.1)
        
        # Uses GTTS to convert the message to an audio file
        tts = gTTS(text=message, lang='en')
        temp_audio_file = "audio.mp3"  # Default to mp3
        
        # Remove old audio files if they exist
        for old_file in ["audio.mp3", "audio.wav"]:
            try:
                if os.path.exists(old_file):
                    os.remove(old_file)
            except Exception as e:
                log(f"Warning: Could not remove old {old_file}: {e}")
        
        tts.save("audio.mp3")

        # Try to convert the audio file to a .wav file (requires ffmpeg)
        # WAV is more universal across different operating systems, but MP3 works too
        try:
            audio = AudioSegment.from_mp3("audio.mp3")
            audio.export("audio.wav", format="wav")
            temp_audio_file = "audio.wav"
            # Only remove mp3 if conversion succeeded
            try:
                os.remove("audio.mp3")
            except Exception as e:
                log(f"Warning: Could not remove audio.mp3: {e}")
        except FileNotFoundError:
            # ffmpeg not installed - use MP3 directly
            log("Warning: ffmpeg not found. Using MP3 format directly. Install ffmpeg for WAV support.")
            temp_audio_file = "audio.mp3"
        except Exception as e:
            # Other conversion error - fall back to MP3
            log(f"Warning: Audio conversion failed ({e}). Using MP3 format.")
            temp_audio_file = "audio.mp3"

        # Locks the playbackLock to prevent multiple audio files being played at once
        # Plays the audio file
        with playbackLock:
            pygame.mixer.music.load(temp_audio_file)
            pygame.mixer.music.play()

            # Submit cleanup task that will also resume background audio when done
            executor.submit(cleanupAndResumeAudio, temp_audio_file)
        
    except Exception as e:
        log(f"Error in readMessage: {e}")
        # Try to resume background audio even if there was an error
        try:
            streamAudio(state='play')
        except:
            pass

# This function deletes the temporary audio file that was created to play the message
def cleanup(temp_audio_file):
    try:
        # Wait for pygame to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.delay(100)

        # Add a small delay to ensure file is released
        time.sleep(0.2)
        
        # Try to remove the file with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                    log(f"Cleaned up: {temp_audio_file}")
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    log(f"Warning: Could not delete {temp_audio_file} - file may be in use")
            except Exception as e:
                log(f"Error cleaning up {temp_audio_file}: {e}")
                break
    except Exception as e:
        log(f"Error in cleanup function: {e}")

# This function cleans up the audio file AND resumes background music after TTS finishes
def cleanupAndResumeAudio(temp_audio_file):
    try:
        # Wait for pygame to finish playing the TTS
        while pygame.mixer.music.get_busy():
            pygame.time.delay(100)

        # Unload the audio to release the file handle
        try:
            pygame.mixer.music.unload()
        except:
            pass
        
        # Add a small delay to ensure file is released
        time.sleep(0.3)
        
        # Try to remove the file with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                    log(f"Cleaned up: {temp_audio_file}")
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.3)
                else:
                    log(f"Warning: Could not delete {temp_audio_file} - file may be in use")
            except Exception as e:
                log(f"Error cleaning up {temp_audio_file}: {e}")
                break
        
        # Now resume the background audio stream
        try:
            streamAudio(state='play')
            log("Background audio resumed after TTS")
        except Exception as e:
            log(f"Error resuming background audio: {e}")
            
    except Exception as e:
        log(f"Error in cleanupAndResumeAudio function: {e}")
        # Try to resume audio anyway
        try:
            streamAudio(state='play')
        except:
            pass

# This function pauses the audio playback
def pausePlayback():
    with playbackLock:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()

# This function resumes the audio playback
def resumePlayback():
    with playbackLock:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.unpause()

# This function stops the audio playback completely
def stopPlayback():
    with playbackLock:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

# This function creates the GUI for the user to select what monitor to display the game on
def chooseMonitor(monitors):
    global defaultMonitor
    
    chooseMonitor = Tk()
    chooseMonitor.title("Choose Monitor")
    chooseMonitor.geometry("500x200")
    chooseMonitor.resizable(False, False)

    monitorLabel = Label(chooseMonitor, text="Choose a monitor to display the game on:", font=("Arial", 20))
    monitorLabel.pack(pady=10)

    monitorVar = IntVar()
    monitorVar.set(0)

    for index, monitor in enumerate(monitors):
        monitorButton = Radiobutton(chooseMonitor, text=f"{monitor.name} - {monitor.width}x{monitor.height}", font=("Arial", 15), variable=monitorVar, value=index)
        monitorButton.pack()

    # This function sets the default monitor to the one selected by the user
    def confirmMonitor():
        global defaultMonitor
        defaultMonitor = monitorVar.get()
        chooseMonitor.destroy()

    confirmButton = Button(chooseMonitor, text="Confirm", font=("Arial", 15), command=confirmMonitor)
    confirmButton.pack(pady=10)

    chooseMonitor.mainloop()

# This function controls the process of selecting the primary monitor and returns the information about the monitor
def choosePrimaryMonitor():
    global defaultMonitor

    monitors = get_monitors()

    if len(monitors) > 1:
        chooseMonitor(monitors)
    
    else:
        defaultMonitor = 0

    primary_monitor = monitors[defaultMonitor]
    return primary_monitor.width, primary_monitor.height

# This function sets the screen dimensions and sets the scaling variables for the GUI
def setScreenDimensions():
    global screenWidth, screenHeight, scaleWidth, scaleHeight
    screenWidth, screenHeight = choosePrimaryMonitor()

    scaleWidth = round(screenWidth / 1920, 2)
    scaleHeight = round(screenHeight / 1080, 2)

# This functions returns the width, height, x and y coordinates of the montior so that the GUI can be displayed on the correct monitor
def getMonitorInfo(monitor_index):
    monitors = get_monitors()
    
    if monitor_index < len(monitors):
        monitor = monitors[monitor_index]
        return monitor.width, monitor.height, monitor.x, monitor.y
    else:
        raise IndexError("Monitor index out of range.")
    
# This function actually moves the GUI to the correct monitor
def setMonitor(monitor_index, window):
    screenWidth, screenHeight, monitor_x, monitor_y = getMonitorInfo(monitor_index)
    
    window.geometry(f"{screenWidth}x{screenHeight}+{monitor_x}+{monitor_y}")
    window.attributes("-fullscreen", True)

# This activates the notifier function when a message is added to the notification queue and controls notifier to prevent multiple notifications at once
def processNotificationQueue():
    global notificationActive, notificationQueue
    try:
        while True:
            if notificationActive == False:
                if len(notificationQueue) > 0:
                    # Thread-safe check and pop
                    try:
                        message = notificationQueue[0]
                        notificationQueue.pop(0)
                        threading.Thread(target=notifier, args=(message,)).start()
                    except IndexError:
                        # Another thread already popped it, continue
                        pass
            time.sleep(0.1)  # Always sleep to avoid busy-waiting
    except Exception as e:
        log(f"Error processing notification queue: {e}")

# This creates the notification label on the GUI with the intended message
def notifier(message):
    global notificationActive

    notificationLabel = Label(welcomeWindow, font=("Arial", int((20 * scaleWidth) * fontScale)), bg='green', fg='black')
    notificationLabel.pack(side=TOP, pady=10)
    notificationActive = True

    tempMessage = ""

    # This loop displays the message on the GUI using a typewriter effect
    for i in range(len(message)):
        tempMessage += message[i]
        notificationLabel.config(text=tempMessage)
        time.sleep(0.05)

    # Keeps the notification on the screen for 2 seconds before removing it
    time.sleep(2)

    notificationLabel.after(0, notificationLabel.destroy)

    notificationActive = False

# This function takes a notification message and adds it to the notification queue
def addNotification(message):
    global notificationQueue
    notificationQueue.append(message)

# This function creates a rectangle with curved corners
def createRoundedRectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    # This defines all the points of the rectangle
    # This is done as we actually draw a polygon in order to create the effect of a rectangle with curved corners
    points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
    return canvas.create_polygon(points, **kwargs, smooth=True)

# This function creates a curved frame for the GUI by utilising the createRoundedRectangle function. Creates the canvas (frame) and then creates the rounded rectangle on top
def createCurvedFrame(parent, width, height, radius=25, bg_colour="#ffffff"):
    canvas = Canvas(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
    canvas.pack_propagate(False)

    createRoundedRectangle(canvas, 10, 10, width-10, height-10, radius=radius, fill=bg_colour, outline="")
    
    return canvas

# This function creates a curved button for the GUI by utilising the createRoundedRectangle function. Creates the canvas (button) and then creates the rounded rectangle on top and adds the text to the button as a label
def createCurvedButton(parent, width, height, radius=20, bgColour = "#ffcc66", bgColourHover = 'white', fgColour = 'black', text = 'Click Me', bgParent = 'black', fontSize = 20, command = None):
    canvas = Canvas(parent, width=width, height = height, bg=bgParent, highlightthickness=0)
    buttonBG = createRoundedRectangle(canvas, 10, 10, width-10, height-10, radius=radius, fill=bgColour, outline="")

    buttonLabel = Label(canvas, text=text, bg = bgColour, font=("Helvetica Neue", int((fontSize * scaleWidth) * fontScale)), fg = fgColour)
    buttonLabel.place(relx=0.5, rely=0.5, anchor=CENTER)

    if command:
        canvas.bind("<Button-1>", lambda event: command())
        buttonLabel.bind("<Button-1>", lambda event: command())

    canvas.bg_id = buttonBG
    canvas.label_id = buttonLabel

    canvas.bind("<Enter>", lambda event: hoverOverCurvedButton(event, canvas, buttonLabel, bgColourHover))
    canvas.bind("<Leave>", lambda event: hoverOffCurvedButton(event, canvas, buttonLabel, bgColour))
    buttonLabel.bind("<Enter>", lambda event: hoverOverCurvedButton(event, canvas, buttonLabel, bgColourHover))
    buttonLabel.bind("<Leave>", lambda event: hoverOffCurvedButton(event, canvas, buttonLabel, bgColour))

    return canvas

# This function changes the background colour of the button and the label when the mouse hovers over it
def hoverOverCurvedButton(event, canvas, label, bgColour):
    canvas.itemconfig(canvas.bg_id, fill=bgColour)
    label.config(bg=bgColour)

# This function changes the background colour of the button and the label back to its original state when the mouse moves off
def hoverOffCurvedButton(event, canvas, label, bgColour):
    canvas.itemconfig(canvas.bg_id, fill=bgColour)
    label.config(bg=bgColour)

# This function changes the default background colour of a curved button and it's respective label
def changeCurvedButtonColour(canvas, label, bgColour):
    canvas.itemconfig(canvas.bg_id, fill=bgColour)
    label.config(bg=bgColour)

# This function unbinds a curved button so that when clicked on or hovered over produces no change
def unbindCurvedButton(canvas, label):
    canvas.unbind("<Enter>")
    canvas.unbind("<Leave>")
    label.unbind("<Enter>")
    label.unbind("<Leave>")

# This function rebinds a curved buttons so that when clicked on or hovered over it produces the desired change
def rebindCurvedButton(canvas, label, bgColour, bgColourHover):
    canvas.bind("<Enter>", lambda event: hoverOverCurvedButton(event, canvas, label, bgColourHover))
    canvas.bind("<Leave>", lambda event: hoverOffCurvedButton(event, canvas, label, bgColour))
    label.bind("<Enter>", lambda event: hoverOverCurvedButton(event, canvas, label, bgColourHover))
    label.bind("<Leave>", lambda event: hoverOffCurvedButton(event, canvas, label, bgColour))

# This function sets up and maintains the websocket with the backend server. It receives the messages and makes sure the respective functions are called with the correct data
async def websocket():
    global serverConnection, websocketConnected, selectedCardPacks
    
    # Create SSL context with better error handling
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    
    max_retries = 3
    retry_count = 0
    card_packs_transferred = False
    
    while retry_count < max_retries:
        try:
            log(f"🔌 Attempting WebSocket connection (attempt {retry_count + 1}/{max_retries})...")
            async with websockets.connect(
                f"wss://{serverURL}/ws/{clientID}",
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=15,
                close_timeout=5,
                max_size=10**6
                # Removed read_limit and write_limit as they're not supported
            ) as websocket:
                websocketConnected = True
                serverConnection = websocket
                
                log("✅ WebSocket connected successfully")
                
                await websocket.send(f'"command: setupWebsocket, gameCode: {gameCode}, deviceID: {clientID}, agentType: host"')
                
                if not card_packs_transferred and selectedCardPacks:
                    threading.Thread(target=safeTransferCardPacks, args=(selectedCardPacks,), daemon=True).start()
                    card_packs_transferred = True
                
                last_ping_time = time.time()
                message_count = 0
                
                while True:
                    try:
                        # Send application-level ping every 30 seconds
                        current_time = time.time()
                        if current_time - last_ping_time >= 30:
                            try:
                                log(f"🏓 Sending application ping (Messages received: {message_count})")
                                await websocket.send(f'"command: ping, gameCode: {gameCode}, deviceID: {clientID}"')
                                last_ping_time = current_time
                                message_count = 0
                            except Exception as e:
                                log(f"❌ Failed to send ping: {e}")
                                break
                        
                        # Use timeout to allow ping checks during idle periods
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            # No message received, continue to check if ping is needed
                            continue
                        
                        message_count += 1
                        message = message.split(":")
                        
                        if message[0] == 'pong':
                            log("✅ Received pong from server - connection alive")
                            continue
                        if message[0] == 'addUser':
                            addUser(message[1])
                        if message[0] == 'removeUser':
                            removeUser(message[1])
                        if message[0] == 'blackCard':
                            message = ':'.join(message[1:])
                            message = message.replace(":", " ", 1)
                            insertBlackCard(message)
                        if message[0] == 'updateAnswerCount':
                            updateAnswerCount()
                        if 'updateVoteCount' in message[0]:
                            temp = message[0].split("/")
                            updateVoteCount(temp[1], temp[2])
                        if message[0] == 'answers':
                            insertAnswers(message[1])
                        if message[0] == 'cardPacksTransferred':
                            addNotification("Card packs transferred successfully")
                            try:
                                joinGameCanvas.itemconfig(gameCodeLabel, text=gameCode)
                                userLabel.config(text="Waiting for players...")
                            except Exception:
                                pass
                        if message[0] == 'cardPackRequest':
                            uploadCustomCardPack(message[1]) 
                        if message[0] == 'playerScores':   
                            insertPlayerScores(message[1])
                            
                    except websockets.exceptions.ConnectionClosed as e:
                        log(f"⚠️ WebSocket connection closed: {e}")
                        log(f"📊 Final latency: {websocket.latency:.3f}s" if hasattr(websocket, 'latency') else "📊 Latency unavailable")
                        break
                    except Exception as e:
                        log(f"⚠️ Error receiving WebSocket message: {e}")
                        continue
                        
        except Exception as e:
            log(f"❌ WebSocket connection error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                wait_time = min(2 ** retry_count, 10)
                log(f"🔄 Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                log("❌ Max retries reached. WebSocket connection failed.")
                return
        finally:
            websocketConnected = False
            serverConnection = None
            log("🔌 WebSocket disconnected")

# This function sends the requested message to the backend server via the websocket connection
async def sendMessageToServerAsync(message):
    global serverConnection, websocketSendLock
    try:
        if serverConnection:
            # Use lock to prevent message interleaving
            with websocketSendLock:
                await serverConnection.send(message)
                log(f"📤 Sent: {message[:100]}...")  # Log first 100 chars
    except websockets.exceptions.ConnectionClosed:
        log("Cannot send message: WebSocket connection is closed")
    except websockets.exceptions.ConnectionClosedError:
        log("Cannot send message: WebSocket connection is closed")
    except websockets.exceptions.ConnectionClosedOK:
        log("Cannot send message: WebSocket connection was closed normally")
    except Exception as e:
        log(f"Error sending message to server: {e}")

def sendMessageToServer(message):
    try:
        # Create a new event loop if we're in a thread without one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If loop is already running, schedule the coroutine
            asyncio.create_task(sendMessageToServerAsync(message))
        else:
            loop.run_until_complete(sendMessageToServerAsync(message))
    except Exception as e:
        log(f"Error in sendMessageToServer: {e}")
        messagebox.showerror("Error sending message to server", str(e))

# This function changes the game state of the local host and sends the update to the backend server via the sendMessageToServer function
def changeGameState(gameState, answersRequired=0):
    try:
        if gameState == "playing":
            data = f"command: changeGameState, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, gameState: {gameState}, answersRequired: {answersRequired}"
        else:
            data = f"command: changeGameState, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, gameState: {gameState}"
        sendMessageToServer(data)
    except Exception as e:
        messagebox.showerror("Error changing game state", e)

# This function adds the new user to the users list, updates the GUI if necessary and creates a notification
def addUser(username):
    global maxPlayers
    try:
        if username not in users:
            users.append(username)
            # Safely update GUI elements only if they exist
            try:
                if 'joinGameCanvas' in globals() and getattr(joinGameCanvas, 'winfo_exists', lambda: False)():
                    try:
                        joinGameCanvas.itemconfig(playerCountLabel, text=f"Players: {len(users)}/{maxPlayers}")
                    except Exception:
                        pass
            except Exception:
                pass

            addNotification(f"User {username} has joined the game")
            if readAloud == 'On':
                readMessage(f"User {username} has joined the game")
    except Exception as e:
        # Do not show GUI error popups for background join events; log instead
        log(f"Error adding user (non-fatal): {e}")

    try:
        updateDisplayedUsers()
    except:
        pass

# This function removes the user from the users list, updates the GUI if necessary and creates a notification
def removeUser(username):
    try:
        if username in users:
            users.remove(username)
            # Safely update GUI elements only if they exist
            try:
                if 'joinGameCanvas' in globals() and getattr(joinGameCanvas, 'winfo_exists', lambda: False)():
                    try:
                        joinGameCanvas.itemconfig(playerCountLabel, text=f"Players: {len(users)}")
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if 'totalPlayersLabel' in globals() and getattr(totalPlayersLabel, 'winfo_exists', lambda: False)():
                    try:
                        totalPlayersLabel.config(text=f'Total Players: {len(users)}/{maxPlayers}')
                    except Exception:
                        pass
            except Exception:
                pass

            addNotification(f"User {username} has left the game")
            try:
                updateDisplayedUsers()
            except Exception:
                pass
            if readAloud == 'On':
                readMessage(f"User {username} has left the game")
    except Exception as e:
        messagebox.showerror("Error removing user", e)

# This function adjusts the max and min variables and then updates the respective pages to match
def showNextPage(tables, source, cardPackName=None, cardType=None):
    global min, max, currentPage, pages
    
    if min + 9 < len(tables):
        min += 9
    else:
        min = len(tables) - (len(tables) % 9 or 9)

    max = min + 9 if min + 9 < len(tables) else len(tables)

    if currentPage <= pages - 1:
        currentPage += 1

    if readAloud == 'On':
        readMessage(f"You are now viewing page {currentPage} of {int(pages)}")
    
    if source == 'preExisting':
        fillExisitingCardsTable(tables)
        pageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'createGame-Black':
        fillBlackCardsTable(tables)
        blackCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'createGame-White':
        fillWhiteCardsTable(tables)
        whiteCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'preExistingCards':
        fillInExistingCards(cardType, cardPackName)
        preExistingCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")

# This function adjusts the max and min variables and then updates the respective pages to match
def showPreviousPage(tables, source, cardPackName=None, cardType=None):
    global min, max, currentPage, pages
    
    if min - 9 >= 0:
        min -= 9
    else:
        min = 0  # Reset to the beginning if at the start

    max = min + 9 if min + 9 < len(tables) else len(tables)  # Ensure max is updated correctly

    if currentPage > 1:
        currentPage -= 1

    if readAloud == 'On':
        readMessage(f"You are now viewing page {currentPage} of {int(pages)}")

    if source == 'preExisting':
        fillExisitingCardsTable(tables)
        pageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'createGame-Black':
        fillBlackCardsTable(tables)
        blackCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'createGame-White':
        fillWhiteCardsTable(tables)
        whiteCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")
    if source == 'preExistingCards':
        fillInExistingCards(cardType, cardPackName)
        preExistingCardsPageCounter.config(text=f"Page {currentPage}/{int(pages)}")

# This function calculates how much pages will be needed based on the length of the list (table)
def calculatePages(tables, source):
    global pages, currentPage
    pages = len(tables) / 9
    if pages == 0.0:
        pages = 1
    if pages % 1 != 0:
        pages += 1
    currentPage = 1

    if source == 'preExisting':
        pageCounter.config(text=f"Page {str(currentPage)}/{str(int(pages))}")
    if source == 'createGame-Black':
        blackCardsPageCounter.config(text=f"Page {str(currentPage)}/{str(int(pages))}")
    if source == 'createGame-White':
        whiteCardsPageCounter.config(text=f"Page {str(currentPage)}/{str(int(pages))}")
    if source == 'preExistingCards':
        preExistingCardsPageCounter.config(text=f"Page {str(currentPage)}/{str(int(pages))}")

# This function grabs the local IP Address of the laptop (Development use only)
def getIPAddress():
    hostname = socket.gethostname()  # Get the hostname of the machine
    ip_address = socket.gethostbyname(hostname)  # Get the IP address based on the hostname
    return ip_address

# This function generates a QRCode based on the data and saves it as an image in a variable
def generateQRCode(data, bgColour, size=5):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(back_color=bgColour)
    return qr_img

# This function requests for a unique identifer 8 digit code from the backend server
def generateUniqueID():
    try:
        global clientID
        response = requests.get(f"{base_url}/uniqueID")
        clientID = response.json()[0]
    except Exception as e:
        messagebox.showerror("Error generating unique ID", e)
        return False
    
# This function requests for a unique 6 digit game code from the backend server 
def getGameCode():
    try:
        response = requests.get(f"{base_url}/getCode")
        global gameCode
        gameCode = int(response.json()["game_code"])
        threading.Thread(target=asyncio.run, args=(websocket(),)).start()
    except Exception as e:
        messagebox.showerror("Error getting game code", e)
        exit()

# Add this new function for graceful WebSocket shutdown
async def closeWebSocket():
    global serverConnection, websocketConnected
    try:
        websocketConnected = False
        if serverConnection and hasattr(serverConnection, 'close'):
            await serverConnection.close()
        serverConnection = None
    except Exception as e:
        # Suppress WebSocket closing errors as they're expected during shutdown
        pass

# This function ends the whole script, making sure the database is closed correctly
def closeApplication():
    if readAloud == 'On':
        readMessage("Closing the application")
    try:
        # Close WebSocket connection gracefully
        if serverConnection:
            asyncio.run(closeWebSocket())
    except Exception:
        # Suppress any asyncio/WebSocket errors during shutdown
        pass
    try:
        conn.close()
    except Exception:
        pass
    os._exit(0)

# This function stops and removes the loading animation
def endLoadingAnimation():
    time.sleep(2)
    global animation
    animation = False

# This function creates the loading animation
def loadingAnimation():
    global loadingIcon, tkLoadingIcon, loadingLabel, originalLoadingIcon, angle, animation
    originalLoadingIcon = Image.open("Images/Loading.png")
    loadingIcon = originalLoadingIcon
    tkLoadingIcon = ImageTk.PhotoImage(loadingIcon)

    loadingLabel = Label(welcomeWindow, image=tkLoadingIcon, bg="black", borderwidth=0, highlightthickness=0)
    loadingLabel.place(relx=0.5, rely=0.65, anchor=CENTER)

    angle = 0
    animation = True
    animate()

# This function causes the loading animation to rotate thus producing the animation
def animate():
    global angle, loadingIcon, tkLoadingIcon, loadingLabel, animation
    if animation == True:
        angle += 10
        loadingIcon = originalLoadingIcon.rotate(angle)
        tkLoadingIcon = ImageTk.PhotoImage(loadingIcon)
        loadingLabel.config(image=tkLoadingIcon)
        loadingLabel.after(100, animate)
    else:
        loadingLabel.destroy()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS  # Folder where PyInstaller stores temp files
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# This function imports any needed images
def importImages():
    global skipLogo
    skipLogo = PhotoImage(file=resource_path("Images/Skip Logo.png"))

# This function creates the welcome window. It adds all the necessary labels and buttons
def buildWelcomeWindow():
    global welcomeWindow, welcomeWindowCanvas, welcomeTitle, optionsCanvas, createGameButton, customCardPacksButton, settingsButton
    # Deletes any potential canvas's that might be there already. This saves memory and keeps the window organised
    try:
        newCardPackCanvas.destroy()
    except:
        pass

    try:
        scoreboardCanvas.destroy()
    except:
        pass

    try:
        settingsWindowCanvas.destroy()
    except:
        pass

    try:
        # Creates the canvas for all the labels and buttons to appear on
        global welcomeWindowCanvas
        welcomeWindowCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
        welcomeWindowCanvas.place(relwidth=1, relheight=1)

        global welcomeTitle
        welcomeTitle = welcomeWindowCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text="Devices Against Humanity", font=("Helvetica Neue", int((60 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

        global optionsCanvas
        optionsCanvas = createCurvedFrame(welcomeWindowCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
        optionsCanvas.place(relx=0.06, rely=0.2)

        global createGameButton
        createGameButton = createCurvedButton(optionsCanvas, int(690 * scaleWidth), int(225 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text="Create Game", fontSize= 40, command=lambda: buildCreateGameWindow())
        createGameButton.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.3)

        global customCardPacksButton
        customCardPacksButton = createCurvedButton(optionsCanvas, int(690 * scaleWidth), int(225 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text="Custom Card Packs", fontSize=40, command=lambda: buildCardPackWindow())
        customCardPacksButton.place(relx=0.05, rely=0.35, relwidth=0.9, relheight=0.3)

        global settingsButton
        settingsButton = createCurvedButton(optionsCanvas, int(690 * scaleWidth), int(225 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text="Settings", fontSize=40, command=lambda: buildSettingsWindow())
        settingsButton.place(relx=0.05, rely=0.65, relwidth=0.9, relheight=0.3)

        global instructionsCanvas
        instructionsCanvas = createCurvedFrame(welcomeWindowCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
        instructionsCanvas.place(relx=0.54, rely=0.2)

        ipAddress = getIPAddress()
        qrCode = generateQRCode(f"https://devicesagainsthumanity.bgodfrey.org", "#8087a2", 5 * scaleWidth)

        global welcomeInstructions
        welcomeInstructions = Label(instructionsCanvas, text=f"To Setup a Game:\n1. Click Create Game\n2. Choose your card packs\n3. Join via your mobile device at devicesagainsthumanity.bgodfrey.org or scan via QR Code below\n\nTo Create/Edit Custom Card Packs:\n1. Click Custom Card Packs\n2. Click on a card pack to edit it or create a new card pack\n3. Click on a card to edit it\n4. Click 'Add Card' to add a new card\n5. Click 'Delete' to delete a card\n6. Click 'Move' to move a card to another pack", font=("Helvetica Neue", int((18 * scaleHeight) * fontScale)), bg="#8087a2", fg="#eaeaea", wraplength=screenWidth * 0.35, justify=LEFT)
        welcomeInstructions.place(relx=0.5, rely=0.05, anchor=N)

        global qrCodeImage
        qrCodeImage = ImageTk.PhotoImage(qrCode)
        qrCodeLabel = Label(instructionsCanvas, image=qrCodeImage, bg="#8087a2")
        qrCodeLabel.place(relx=0.5, rely=0.825, anchor=CENTER)

        global exitToDesktopButton
        exitToDesktopButton = createCurvedButton(welcomeWindowCanvas, int(500 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Exit to Desktop", bgParent="#24273a", command=lambda: closeApplication())
        exitToDesktopButton.place(relx=0.5, rely=0.95, anchor=CENTER)

        # If needed this reads out information about the current screen and the options the user has
        if readAloud == 'On':
            readMessage("Welcome to Devices Against Humanity! You are on the welcome screen! Here you can create a new game, edit custom card packs or change settings. To create a new game, click the 'Create Game' button. To edit custom card packs, click the 'Custom Card Packs' button. To change settings, click the 'Settings' button. To exit to the desktop, click the 'Exit to Desktop' button.")

    except Exception as e:
        messagebox.showerror("Error building welcome window", e)
        exit()

# This function creates the create game window. It adds all the necessary labels and buttons
def buildCreateGameWindow():
    # Deletes welcomeWindowCanvas as that would be there beforehand and needs removing
    try:
        global welcomeWindowCanvas
        welcomeWindowCanvas.destroy()
    except:
        pass

    try:
        global selectedCardPacks
        selectedCardPacks = []
    except:
        pass

    # Resets all values back to default as to avoid errors
    try:
        global min, max, currentPage, pages
        min = 0
        max = 9
        currentPage = 1
        pages = 0
    except:
        pass

    # Finds all the card packs and sorts them
    cardPacks = findCardPacks('createGameWindow')
    whiteCards = []
    blackCards = []
    for cardPack in cardPacks:
        if cardPack[0] == '0':
            blackCards.append(cardPack)
        elif cardPack[0] == '1':
            whiteCards.append(cardPack)

    # Creates the canvas for all the labels and buttons to be placed onto
    global createGameWindowCanvas
    createGameWindowCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
    createGameWindowCanvas.place(relwidth=1, relheight=1)

    global backButton
    backButton = createCurvedButton(createGameWindowCanvas, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Back", bgParent="#24273a", command=lambda: buildWelcomeWindow())
    backButton.place(relx=0.06, rely=0.07)

    global pageTitle
    pageTitle = createGameWindowCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text="Create Game", font=("Helvetica Neue", int((60 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    global blackCardsCanvas
    blackCardsCanvas = createCurvedFrame(createGameWindowCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    blackCardsCanvas.place(relx=0.06, rely=0.16)

    global blackCardsButtons
    blackCardsButtons = createCurvedFrame(createGameWindowCanvas, screenWidth * 0.4, screenHeight * 0.06, radius=25, bg_colour="#24273a")
    blackCardsButtons.place(relx=0.06, rely=0.86)

    global blackCardsPreviousPageButton
    blackCardsPreviousPageButton = createCurvedButton(blackCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text="<", bgParent='#24273a', command=lambda: showPreviousPage(blackCards, 'createGame-Black'))
    blackCardsPreviousPageButton.pack(side=LEFT, padx=80)

    global blackCardsNextPageButton
    blackCardsNextPageButton = createCurvedButton(blackCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text=">", bgParent='#24273a', command=lambda: showNextPage(blackCards, 'createGame-Black'))
    blackCardsNextPageButton.pack(side=RIGHT, padx=80)

    global blackCardsPageCounter
    blackCardsPageCounter = Label(blackCardsButtons, text="Page 1", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#24273a", fg="#cad3f5")
    blackCardsPageCounter.place(relx=0.5, rely=0.5, anchor=CENTER)

    calculatePages(blackCards, 'createGame-Black')

    global whiteCardsCanvas
    whiteCardsCanvas = createCurvedFrame(createGameWindowCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    whiteCardsCanvas.place(relx=0.54, rely=0.16)

    global whiteCardsButtons
    whiteCardsButtons = createCurvedFrame(createGameWindowCanvas, screenWidth * 0.4, screenHeight * 0.06, radius=25, bg_colour="#24273a")
    whiteCardsButtons.place(relx=0.54, rely=0.86)

    global whiteCardsPreviousPageButton
    whiteCardsPreviousPageButton = createCurvedButton(whiteCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text="<", bgParent='#24273a', command=lambda: showPreviousPage(whiteCards, 'createGame-White'))
    whiteCardsPreviousPageButton.pack(side=LEFT, padx=80)

    global whiteCardsNextPageButton
    whiteCardsNextPageButton = createCurvedButton(whiteCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text=">", bgParent='#24273a', command=lambda: showNextPage(whiteCards, 'createGame-White'))
    whiteCardsNextPageButton.pack(side=RIGHT, padx=80)

    global whiteCardsPageCounter
    whiteCardsPageCounter = Label(whiteCardsButtons, text="Page 1", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#24273a", fg="#cad3f5")
    whiteCardsPageCounter.place(relx=0.5, rely=0.5, anchor=CENTER)

    calculatePages(whiteCards, 'createGame-White')
    
    fillBlackCardsTable(blackCards)
    fillWhiteCardsTable(whiteCards)

    global startGameButton
    startGameButton = createCurvedButton(createGameWindowCanvas, int(500 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover='#7a7a7a', fgColour="#f5f5f5", bgParent='#24273a', text="Start Game", command=lambda: buildJoinGameWindow())
    startGameButton.place(relx=0.5, rely=0.96, anchor=CENTER)

    # If needed this reads out about the current screen and the current options
    if readAloud == 'On':
        readMessage("You are now on the create game screen! Here you can choose the card packs for your game. To add a card pack, click on the card pack you want to add. To remove a card pack, click on the card pack again. To start the game, click the 'Start Game' button.")

# This function creates the card pack window. It adds all the necessary labels and buttons
def buildCardPackWindow():
    # Deletes welcomeWindowCanvas as that would be there beforehand and needs removing
    try:
        global welcomeWindowCanvas
        welcomeWindowCanvas.destroy()
    except:
        pass

    try:
        global editCardPackCanvas
        editCardPackCanvas.destroy()
    except:
        pass

    # Resets all values back to default as to avoid errors
    try:
        global min, max, currentPage, pages
        min = 0
        max = 9
        currentPage = 1
        pages = 0
    except:
        pass

    # Creates the canvas for all the labels and buttons to be placed onto
    global newCardPackCanvas
    newCardPackCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
    newCardPackCanvas.place(relwidth=1, relheight=1)

    global backButton
    backButton = createCurvedButton(newCardPackCanvas, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Back", bgParent="#24273a", command=lambda: buildWelcomeWindow())
    backButton.place(relx=0.06, rely=0.07)

    global pageTitle
    pageTitle = newCardPackCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text="Edit Custom Card Packs", font=("Helvetica Neue", int((60 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    global preExistingCardPacksCanvas
    preExistingCardPacksCanvas = createCurvedFrame(newCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    preExistingCardPacksCanvas.place(relx=0.06, rely=0.2)

    global preExistingCardPacksLabel
    preExistingCardPacksLabel = Label(preExistingCardPacksCanvas, text="No available Card Packs", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    preExistingCardPacksLabel.place(relx=0.5, rely=0.5, anchor=CENTER)

    fillExisitingCardsTable(findCardPacks())

    global pageButtons
    pageButtons = createCurvedFrame (newCardPackCanvas, screenWidth * 0.4, screenHeight * 0.06, radius=25, bg_colour="#24273a")
    pageButtons.place(relx=0.06, rely=0.9)

    global previousPageButton
    previousPageButton = createCurvedButton(pageButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text="<", bgParent='#24273a', command=lambda: showPreviousPage(findCardPacks(), 'preExisting'))
    previousPageButton.pack(side=LEFT, padx=80)

    global nextPageButton
    nextPageButton = createCurvedButton(pageButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text=">", bgParent='#24273a', command=lambda: showNextPage(findCardPacks(), 'preExisting'))
    nextPageButton.pack(side=RIGHT, padx=80)

    global pageCounter
    pageCounter = Label(pageButtons, text="Page 1", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#24273a", fg="#cad3f5")
    pageCounter.place(relx=0.5, rely=0.5, anchor=CENTER)

    calculatePages(findCardPacks(), 'preExisting')

    global createNewCardPackCanvas
    createNewCardPackCanvas = createCurvedFrame(newCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    createNewCardPackCanvas.place(relx=0.54, rely=0.2)

    global newCardPackTitle
    newCardPackTitle = Label(createNewCardPackCanvas, text="New Card Pack", font=("Helvetica Neue", int((50 * scaleWidth) * fontScale)), bg="#8087a2", fg="#b8c0e0", pady=10)
    newCardPackTitle.place(relx=0.5, rely=0.1, anchor=CENTER)

    global newCardPackNameLabel
    newCardPackNameLabel = Label(createNewCardPackCanvas, text="Name:", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea", pady=10)
    newCardPackNameLabel.place(relx=0.5, rely=0.3, anchor=CENTER)

    global newCardPackNameEntry
    newCardPackNameEntry = Entry(createNewCardPackCanvas, font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#eaeaea", fg="#333333", relief="flat", highlightbackground="#555555", highlightthickness=1)
    newCardPackNameEntry.place(relx=0.5, rely=0.4, anchor=CENTER)

    global newCardPackTypeLabel
    newCardPackTypeLabel = Label(createNewCardPackCanvas, text="Type:", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea", pady=10)
    newCardPackTypeLabel.place(relx=0.5, rely=0.55, anchor=CENTER)

    def setCardType(type):
        global cardType
        if type == 'black':
            cardType = 'black'
            changeCurvedButtonColour(newCardPackTypeWhite, newCardPackTypeWhite.label_id, 'white')
            changeCurvedButtonColour(newCardPackTypeBlack, newCardPackTypeBlack.label_id, 'green')
            unbindCurvedButton(newCardPackTypeBlack, newCardPackTypeBlack.label_id)
            rebindCurvedButton(newCardPackTypeWhite, newCardPackTypeWhite.label_id, 'white', 'grey')
        elif type == 'white':
            cardType = 'white'
            changeCurvedButtonColour(newCardPackTypeBlack, newCardPackTypeBlack.label_id, 'black')
            changeCurvedButtonColour(newCardPackTypeWhite, newCardPackTypeWhite.label_id, 'green')
            unbindCurvedButton(newCardPackTypeWhite, newCardPackTypeWhite.label_id)
            rebindCurvedButton(newCardPackTypeBlack, newCardPackTypeBlack.label_id, 'black', 'grey')

    global buttonContainer
    buttonContainer = Frame(createNewCardPackCanvas, bg="#8087a2")
    buttonContainer.place(relx=0.5, rely=0.65, anchor=CENTER)

    newCardPackTypeBlack = createCurvedButton(buttonContainer, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover='grey', fgColour="white", text="Black", bgParent='#8087a2', command=lambda: setCardType('black'))
    newCardPackTypeBlack.pack(side=LEFT, padx=20)

    newCardPackTypeWhite = createCurvedButton(buttonContainer, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="white", bgColourHover='grey', fgColour="black", text="White", bgParent='#8087a2', command=lambda: setCardType('white'))
    newCardPackTypeWhite.pack(side=LEFT, padx=20)

    global newCardPackSubmit
    newCardPackSubmit = createCurvedButton(createNewCardPackCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover='#7a7a7a', fgColour="#f5f5f5", bgParent='#8087a2', text="Create", command=lambda: createNewCardPack(newCardPackNameEntry.get(), cardType))
    newCardPackSubmit.place(relx=0.5, rely=0.85, anchor=CENTER)

    # If needed this reads out information about the screen and what the user can do
    if readAloud == 'On':
        readMessage("You are now on the custom card packs screen! Here you can create a new card pack or edit an existing card pack. To create a new card pack, enter a name, select the type and click 'Create'. To edit an existing card pack, click on the card pack you want to edit.")

# This function creates the settings window. It adds all the necessary labels and buttons
def buildSettingsWindow():
    #Deletes welcomeWindowCanvas as that would be there beforehand and needs removing
    try:
        global welcomeWindowCanvas
        welcomeWindowCanvas.destroy()
    except:
        pass

    # Creates the canvas for the labels and buttons to be placed onto
    global settingsWindowCanvas
    settingsWindowCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
    settingsWindowCanvas.place(relwidth=1, relheight=1)

    global backButton
    backButton = createCurvedButton(settingsWindowCanvas, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Back", bgParent="#24273a", command=lambda: buildWelcomeWindow())
    backButton.place(relx=0.06, rely=0.07)

    global pageTitle
    pageTitle = settingsWindowCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text="Settings", font=("Helvetica Neue", int((60 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    global gameSettingsCanvas
    gameSettingsCanvas = createCurvedFrame(settingsWindowCanvas, screenWidth * 0.4, screenHeight * 0.8, radius=25, bg_colour="#8087a2")
    gameSettingsCanvas.place(relx=0.06, rely=0.16)

    global cardPackSettingsCanvas
    cardPackSettingsCanvas = createCurvedFrame(settingsWindowCanvas, screenWidth * 0.4, screenHeight * 0.25, radius=25, bg_colour="#8087a2")
    cardPackSettingsCanvas.place(relx=0.54, rely=0.16)

    global accessibilitySettingsCanvas
    accessibilitySettingsCanvas = createCurvedFrame(settingsWindowCanvas, screenWidth * 0.4, screenHeight * 0.45, radius=25, bg_colour="#8087a2")
    accessibilitySettingsCanvas.place(relx=0.54, rely=0.51)

    global gameSettingsTitle
    gameSettingsTitle = Label(gameSettingsCanvas, text="Game Settings", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea", pady=10)
    gameSettingsTitle.place(relx=0.5, rely=0.1, anchor=CENTER)

    global cardPackSettingsTitle
    cardPackSettingsTitle = Label(cardPackSettingsCanvas, text="Card Pack Settings", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea", pady=10)
    cardPackSettingsTitle.place(relx=0.5, rely=0.176, anchor=CENTER)

    global accessibilitySettingsTitle
    accessibilitySettingsTitle = Label(accessibilitySettingsCanvas, text="Accessibility Settings", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea", pady=10)
    accessibilitySettingsTitle.place(relx=0.5, rely=0.1, anchor=CENTER)

    global cardPackSettingsFrame
    cardPackSettingsFrame = Frame(cardPackSettingsCanvas, bg="#8087a2")
    cardPackSettingsFrame.place(relx=0.5, rely=0.45, anchor=CENTER)

    global accessibilitySettingsFrame
    accessibilitySettingsFrame = Frame(accessibilitySettingsCanvas, bg="#8087a2")
    accessibilitySettingsFrame.place(relx=0.5, rely=0.5, anchor=CENTER)

    global gameSettingsFrame
    gameSettingsFrame = Frame(gameSettingsCanvas, bg="#8087a2")
    gameSettingsFrame.place(relx=0.5, rely=0.5, anchor=CENTER)

    global cardPackSettingsRevertButton
    cardPackSettingsRevertButton = createCurvedButton(cardPackSettingsCanvas, int(700 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Revert back to default", bgParent="#8087a2", fontSize=18, command=lambda: revertCardPackSettingsToDefault())
    cardPackSettingsRevertButton.place(relx=0.5, rely=0.7, anchor=CENTER)

    global accessibilitySettingsRevertButton
    accessibilitySettingsRevertButton = createCurvedButton(accessibilitySettingsCanvas, int(700 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Revert back to default", bgParent="#8087a2", fontSize=18, command=lambda: revertAccessibilitySettingsToDefault())
    accessibilitySettingsRevertButton.place(relx=0.5, rely=0.8, anchor=CENTER)

    global gameSettingsRevertButton
    gameSettingsRevertButton = createCurvedButton(gameSettingsCanvas, int(700 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Revert back to default", bgParent="#8087a2", fontSize=18, command=lambda: revertGameSettingsToDefault())
    gameSettingsRevertButton.place(relx=0.5, rely=0.9, anchor=CENTER)

    global cardPackSettingsErrorLabel
    cardPackSettingsErrorLabel = Label(cardPackSettingsCanvas, text="", font=("Helvetica Neue", int((15 * scaleWidth) * fontScale)), bg="#8087a2", fg="red")
    cardPackSettingsErrorLabel.place(relx=0.5, rely=0.875, anchor=CENTER)

    global accessibilitySettingsErrorLabel
    accessibilitySettingsErrorLabel = Label(accessibilitySettingsCanvas, text="", font=("Helvetica Neue", int((15 * scaleWidth) * fontScale)), bg="#8087a2", fg="red")
    accessibilitySettingsErrorLabel.place(relx=0.5, rely=0.925, anchor=CENTER)

    global gameSettingsErrorLabel
    gameSettingsErrorLabel = Label(gameSettingsCanvas, text="", font=("Helvetica Neue", int((15 * scaleWidth) * fontScale)), bg="#8087a2", fg="red")
    gameSettingsErrorLabel.place(relx=0.5, rely=0.96, anchor=CENTER)

    global maxPlayersLabel
    maxPlayersLabel = Label(gameSettingsFrame, text="Max Players:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    maxPlayersLabel.grid(row=0, column=0, padx=20, pady=10)

    global maxPlayersCurrentSettingLabel
    maxPlayersCurrentSettingLabel = Label(gameSettingsFrame, text="20", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    maxPlayersCurrentSettingLabel.grid(row=0, column=1, padx=20, pady=10)

    global maxPlayersButtonsFrame
    maxPlayersButtonsFrame = Frame(gameSettingsFrame, bg="#8087a2")
    maxPlayersButtonsFrame.grid(row=0, column=2, padx=10, pady=10)

    global maxPlayersIncreaseButton
    maxPlayersIncreaseButton = createCurvedButton(maxPlayersButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeMaxPlayers('increase'))
    maxPlayersIncreaseButton.grid(row=0, column=0)

    global maxPlayersDecreaseButton
    maxPlayersDecreaseButton = createCurvedButton(maxPlayersButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeMaxPlayers('decrease'))
    maxPlayersDecreaseButton.grid(row=1, column=0)

    global votingMethodLabel
    votingMethodLabel = Label(gameSettingsFrame, text="Voting Method:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    votingMethodLabel.grid(row=1, column=0, padx=20, pady=10)

    global votingMethodCurrentSettingLabel
    votingMethodCurrentSettingLabel = Label(gameSettingsFrame, text="Multi-voting", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    votingMethodCurrentSettingLabel.grid(row=1, column=1, padx=20, pady=10)

    global votingMethodButton
    votingMethodButton = createCurvedButton(gameSettingsFrame, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Switch", bgParent="#8087a2", fontSize=18, command=lambda: switchVotingMethod())
    votingMethodButton.grid(row=1, column=2, padx=10, pady=10)

    global numberOfRoundsLabel
    numberOfRoundsLabel = Label(gameSettingsFrame, text="Number of Rounds:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    numberOfRoundsLabel.grid(row=2, column=0, padx=20, pady=10)

    global numberOfRoundsCurrentSettingLabel
    numberOfRoundsCurrentSettingLabel = Label(gameSettingsFrame, text="10", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    numberOfRoundsCurrentSettingLabel.grid(row=2, column=1, padx=20, pady=10)

    global numberOfRoundsButtonsFrame
    numberOfRoundsButtonsFrame = Frame(gameSettingsFrame, bg="#8087a2")
    numberOfRoundsButtonsFrame.grid(row=2, column=2, padx=10, pady=10)

    global numberOfRoundsIncreaseButton
    numberOfRoundsIncreaseButton = createCurvedButton(numberOfRoundsButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeNumberOfRounds('increase'))
    numberOfRoundsIncreaseButton.grid(row=0, column=0)

    global numberOfRoundsDecreaseButton
    numberOfRoundsDecreaseButton = createCurvedButton(numberOfRoundsButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeNumberOfRounds('decrease'))
    numberOfRoundsDecreaseButton.grid(row=1, column=0)

    global numberOfRoundsUnlimitedButton
    numberOfRoundsUnlimitedButton = createCurvedButton(numberOfRoundsButtonsFrame, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="white", text="Unlimited", bgParent="#8087a2", fontSize=18, command=lambda: changeNumberOfRounds('unlimited'))
    numberOfRoundsUnlimitedButton.grid(row=0, column=1, rowspan=2, padx=10)

    global questionTimerLabel
    questionTimerLabel = Label(gameSettingsFrame, text="Question Timer:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    questionTimerLabel.grid(row=3, column=0, padx=20, pady=10)

    global questionTimerCurrentSettingLabel
    questionTimerCurrentSettingLabel = Label(gameSettingsFrame, text="60s", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    questionTimerCurrentSettingLabel.grid(row=3, column=1, padx=20, pady=10)

    global questionTimerButtonsFrame
    questionTimerButtonsFrame = Frame(gameSettingsFrame, bg="#8087a2")
    questionTimerButtonsFrame.grid(row=3, column=2, padx=10, pady=10)

    global questionTimerIncreaseButton
    questionTimerIncreaseButton = createCurvedButton(questionTimerButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeQuestionTimer('increase'))
    questionTimerIncreaseButton.grid(row=0, column=0)

    global questionTimerDecreaseButton
    questionTimerDecreaseButton = createCurvedButton(questionTimerButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeQuestionTimer('decrease'))
    questionTimerDecreaseButton.grid(row=1, column=0)

    global votingTimerLabel
    votingTimerLabel = Label(gameSettingsFrame, text="Voting Timer:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    votingTimerLabel.grid(row=4, column=0, padx=20, pady=10)

    global votingTimerCurrentSettingLabel
    votingTimerCurrentSettingLabel = Label(gameSettingsFrame, text="60s", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    votingTimerCurrentSettingLabel.grid(row=4, column=1, padx=20, pady=10)

    global votingTimerButtonsFrame
    votingTimerButtonsFrame = Frame(gameSettingsFrame, bg="#8087a2")
    votingTimerButtonsFrame.grid(row=4, column=2, padx=10, pady=10)

    global votingTimerIncreaseButton
    votingTimerIncreaseButton = createCurvedButton(votingTimerButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeVotingTimer('increase'))
    votingTimerIncreaseButton.grid(row=0, column=0)

    global votingTimerDecreaseButton
    votingTimerDecreaseButton = createCurvedButton(votingTimerButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeVotingTimer('decrease'))
    votingTimerDecreaseButton.grid(row=1, column=0)

    global readCardsOutLabel
    readCardsOutLabel = Label(gameSettingsFrame, text="Read Cards Out:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    readCardsOutLabel.grid(row=5, column=0, padx=20, pady=10)

    global readCardsOutCurrentSettingLabel
    readCardsOutCurrentSettingLabel = Label(gameSettingsFrame, text="Off", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    readCardsOutCurrentSettingLabel.grid(row=5, column=1, padx=20, pady=10)

    global readCardsOutButton
    readCardsOutButton = createCurvedButton(gameSettingsFrame, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Switch", bgParent="#8087a2", fontSize=18, command=lambda: switchReadCardsOut())
    readCardsOutButton.grid(row=5, column=2, padx=10, pady=10)

    global checkConnectionButton
    checkConnectionButton = createCurvedButton(gameSettingsFrame, int(500 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Check Connection", bgParent="#8087a2", fontSize=18, command=lambda: checkConnection())
    checkConnectionButton.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

    global cardPackSizeLabel
    cardPackSizeLabel = Label(cardPackSettingsFrame, text="Max Card Pack Size:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    cardPackSizeLabel.grid(row=0, column=0, padx=20, pady=10)

    global cardPackSizeCurrentSettingLabel
    cardPackSizeCurrentSettingLabel = Label(cardPackSettingsFrame, text="Unlimited", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    cardPackSizeCurrentSettingLabel.grid(row=0, column=1, padx=20, pady=10)

    global cardPackSizeButtonsFrame
    cardPackSizeButtonsFrame = Frame(cardPackSettingsFrame, bg="#8087a2")
    cardPackSizeButtonsFrame.grid(row=0, column=2, padx=10, pady=10)

    global cardPackSizeIncreaseButton
    cardPackSizeIncreaseButton = createCurvedButton(cardPackSizeButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeCardPackSize('increase'))
    cardPackSizeIncreaseButton.grid(row=0, column=0)

    global cardPackSizeDecreaseButton
    cardPackSizeDecreaseButton = createCurvedButton(cardPackSizeButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeCardPackSize('decrease'))
    cardPackSizeDecreaseButton.grid(row=1, column=0)

    global cardPackSizeUnlimitedButton
    cardPackSizeUnlimitedButton = createCurvedButton(cardPackSizeButtonsFrame, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="white", text="Unlimited", bgParent="#8087a2", fontSize=18, command=lambda: changeCardPackSize('unlimited'))
    cardPackSizeUnlimitedButton.grid(row=0, column=1, rowspan=2)

    global fontSizeLabel
    fontSizeLabel = Label(accessibilitySettingsFrame, text="Font Size:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    fontSizeLabel.grid(row=0, column=0, padx=20, pady=10)

    global fontSizeCurrentSettingLabel
    fontSizeCurrentSettingLabel = Label(accessibilitySettingsFrame, text="100%", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    fontSizeCurrentSettingLabel.grid(row=0, column=1, padx=20, pady=10)

    global fontSizeButtonsFrame
    fontSizeButtonsFrame = Frame(accessibilitySettingsFrame, bg="#8087a2")
    fontSizeButtonsFrame.grid(row=0, column=2, padx=10, pady=10)

    global fontSizeIncreaseButton
    fontSizeIncreaseButton = createCurvedButton(fontSizeButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="+", bgParent="#8087a2", fontSize=18, command=lambda: changeFontScale('increase'))
    fontSizeIncreaseButton.grid(row=0, column=0)

    global fontSizeDecreaseButton
    fontSizeDecreaseButton = createCurvedButton(fontSizeButtonsFrame, int(50 * scaleWidth), int(30 * scaleHeight), radius=25, bgColour="#8087a2", bgColourHover="#8087a2", fgColour="white", text="-", bgParent="#8087a2", fontSize=18, command=lambda: changeFontScale('decrease'))
    fontSizeDecreaseButton.grid(row=1, column=0)

    global fontSizeUpdateButton
    fontSizeUpdateButton = createCurvedButton(fontSizeButtonsFrame, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Update", bgParent="#8087a2", fontSize=18)
    fontSizeUpdateButton.grid(row=0, column=1, rowspan=2, padx=10, pady=10)

    global readAloudLabel
    readAloudLabel = Label(accessibilitySettingsFrame, text="Read Aloud:", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    readAloudLabel.grid(row=1, column=0, padx=20, pady=10)

    global readAloudCurrentSettingLabel
    readAloudCurrentSettingLabel = Label(accessibilitySettingsFrame, text="Off", font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    readAloudCurrentSettingLabel.grid(row=1, column=1, padx=20, pady=10)

    global readAloudButton
    readAloudButton = createCurvedButton(accessibilitySettingsFrame, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Switch", bgParent="#8087a2", fontSize=18, command=lambda: switchReadAloud())
    readAloudButton.grid(row=1, column=2, padx=10, pady=10)

    refreshSettingsPage()

    # If needed reads out information about the screen and what the user can do
    if readAloud == 'On':
        readMessage("You are now on the settings screen! Here you can change the game settings, card pack settings and accessibility settings. To change a setting, click on the setting you want to change and use the buttons to change the value.")

# This function creates the edit card pack window. It adds all the necessary labels and buttons
def buildEditCardPackWindow(cardPackName):
    # Deletes the old canvas's that would be there beforehand and need removing
    try:
        global newCardPackCanvas
        newCardPackCanvas.destroy()
    except:
        pass

    try:
        global editCardPackCanvas
        editCardPackCanvas.destroy()
    except:
        pass

    #Resets the global variables for the page for the correct processing
    global min, max, pages, currentPage, answerCount
    min = 0
    max = 9
    pages = 0

    # Gets the card type and uses it to get the cards for the card pack
    cardType = cardPackName[0]
    cards = getCards(cardPackName, cardType)

    editCardPackCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
    editCardPackCanvas.place(relwidth=1, relheight=1)

    global backButton
    backButton = createCurvedButton(editCardPackCanvas, int(150 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Back", bgParent="#24273a", command=lambda: buildCardPackWindow())
    backButton.place(relx=0.06, rely=0.07)

    global pageTitle
    pageTitle = editCardPackCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text=f"Editing Card Pack: {cardPackName[1:]}", font=("Helvetica Neue", int((60 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    global preExistingCardsCanvas
    preExistingCardsCanvas = createCurvedFrame(editCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    preExistingCardsCanvas.place(relx=0.06, rely=0.16)

    global preExistingCardsButtons
    preExistingCardsButtons = createCurvedFrame(editCardPackCanvas, screenWidth * 0.4, screenHeight * 0.06, radius=25, bg_colour="#24273a")
    preExistingCardsButtons.place(relx=0.06, rely=0.86)

    global preExistingCardsNextButton
    preExistingCardsNextButton = createCurvedButton(preExistingCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text=">", bgParent="#24273a", command=lambda: showNextPage(cards, 'preExistingCards', cardPackName=cardPackName, cardType=cardType))
    preExistingCardsNextButton.pack(side=RIGHT, padx=80)

    global preExistingCardsPreviousButton
    preExistingCardsPreviousButton = createCurvedButton(preExistingCardsButtons, int(85 * scaleWidth), int(65 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="<", bgParent="#24273a", command=lambda: showPreviousPage(cards, 'preExistingCards', cardPackName=cardPackName, cardType=cardType))
    preExistingCardsPreviousButton.pack(side=LEFT, padx=80)

    global preExistingCardsPageCounter
    preExistingCardsPageCounter = Label(preExistingCardsButtons, text="Page 1", font=("Helvetica Neue", int((20 * scaleWidth)* fontScale)), bg="#24273a", fg="#eaeaea")
    preExistingCardsPageCounter.place(relx=0.5, rely=0.5, anchor=CENTER)

    global newCardCanvas
    newCardCanvas = createCurvedFrame(editCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    newCardCanvas.place(relx=0.54, rely=0.16)

    global newCardTitle
    newCardTitle = Label(newCardCanvas, text="New Card", font=("Helvetica Neue", int((50 * scaleWidth) * fontScale)), bg="#8087a2", fg="#b8c0e0", pady=10)
    newCardTitle.place(relx=0.5, rely=0.1, anchor=CENTER)

    if cardType == '0':
        global newCardQuestionLabel
        newCardQuestionLabel = Label(newCardCanvas, text="Question:", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea", pady=10)
        newCardQuestionLabel.place(relx=0.5, rely=0.3, anchor=CENTER)

        global newCardQuestionEntry
        newCardQuestionEntry = Entry(newCardCanvas, font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#eaeaea", fg="#333333", width=30)
        newCardQuestionEntry.place(relx=0.5, rely=0.35, anchor=CENTER)

        global newCardQuestionInsertAnswerButton
        newCardQuestionInsertAnswerButton = createCurvedButton(newCardCanvas, int(400 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Insert Answer Space", bgParent="#8087a2", command=lambda: insertAnswerSpace())
        newCardQuestionInsertAnswerButton.place(relx=0.5, rely=0.45, anchor=CENTER)

        global newCardQuestionAnswerCountLabel
        newCardQuestionAnswerCountLabel = Label(newCardCanvas, text="Number of Answers Required:", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea", pady=10)
        newCardQuestionAnswerCountLabel.place(relx=0.5, rely=0.55, anchor=CENTER)

        global answerCount1Button
        answerCount1Button = createCurvedButton(newCardCanvas, int(75 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="1", bgParent="#8087a2", command=lambda: setAnswerCount(1))
        answerCount1Button.place(relx=0.4, rely=0.65, anchor=CENTER)

        global answerCount2Button
        answerCount2Button = createCurvedButton(newCardCanvas, int(75 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="2", bgParent="#8087a2", command=lambda: setAnswerCount(2))
        answerCount2Button.place(relx=0.6, rely=0.65, anchor=CENTER)
    
    elif cardType == '1':
        global newCardAnswerLabel
        newCardAnswerLabel = Label(newCardCanvas, text="Answer:", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea", pady=10)
        newCardAnswerLabel.place(relx=0.5, rely=0.4, anchor=CENTER)

        global newCardAnswerEntry
        newCardAnswerEntry = Entry(newCardCanvas, font=("Helvetica Neue", int((18 * scaleWidth) * fontScale)), bg="#eaeaea", fg="#333333")
        newCardAnswerEntry.place(relx=0.5, rely=0.5, anchor=CENTER)
    
    global addNewCardButton
    addNewCardButton = createCurvedButton(newCardCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Add Card", bgParent="#8087a2", command=lambda: addNewCard(cardType, cardPackName, question=newCardQuestionEntry.get() if cardType == '0' else None, answer=newCardAnswerEntry.get() if cardType == '1' else None, answerNum=str(answerCount) if cardType == '0' else None))
    addNewCardButton.place(relx=0.5, rely=0.8, anchor=CENTER)

    global successOrErrorLabel
    successOrErrorLabel = Label(newCardCanvas, text="", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="red")
    successOrErrorLabel.place(relx=0.5, rely=0.9, anchor=CENTER)

    global deleteCardPackButton
    deleteCardPackButton = createCurvedButton(editCardPackCanvas, int(500 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Delete Card Pack", bgParent="#24273a", command=lambda: deleteCardPack(cardPackName))
    deleteCardPackButton.place(relx=0.5, rely=0.96, anchor=CENTER)

    calculatePages(cards, 'preExistingCards')
    fillInExistingCards(cardType, cardPackName)

    # If needed then reads out information about the screen and what the user can do
    if readAloud == 'On':
        readMessage("You are now on the edit card pack screen! Here you can add new cards to the card pack, delete the card pack or go back to the card pack screen. To add a new card, fill in the fields and click 'Add Card'. To delete the card pack, click 'Delete Card Pack'. If you want to edit a specific card, click on the card.")

# This function creates the join game window. It adds all the necessary labels and buttons
def buildJoinGameWindow():
    # Deletes the old canvas's that would be there beforehand and need removing
    threading.Thread(target=streamAudio, daemon=True).start()
    try:
        try:
            global createGameWindowCanvas
            createGameWindowCanvas.destroy()
        except:
            pass

        # Imports the needed images for the window
        importImages()

        global joinGameCanvas
        joinGameCanvas = Canvas(welcomeWindow, width=welcomeWindow.winfo_width(), height=welcomeWindow.winfo_height(), bg="#24273a", highlightthickness=0)
        joinGameCanvas.place(relwidth=1, relheight=1)

        global gameTitle
        gameTitle = joinGameCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text='Devices Against Humanity', font=("Arial", int((100 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

        global gameCodeLabel
        gameCodeLabel = joinGameCanvas.create_text(screenWidth / 2, screenHeight * 0.285, text="", font=("Arial", int((225 * scaleWidth) * fontScale)), fill="#cad3f5")

        global joinedUsersFrame
        joinedUsersFrame = Frame(welcomeWindow, bg="#24273a")
        joinedUsersFrame.place(relx=0.5, rely=0.6, anchor=CENTER)

        global userLabel
        userLabel = Label(joinedUsersFrame, text="Connecting to server...", font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#24273a", fg="#cad3f5")
        userLabel.grid(row=0, column=0, padx=20, pady=20)

        global playerCountLabel, maxPlayers
        playerCountLabel = joinGameCanvas.create_text(screenWidth / 2, screenHeight * 0.83, text=f"Players: 0/{maxPlayers}", font=("Arial", int((50 * scaleWidth) * fontScale)), fill="#cad3f5")

        global startGameButton
        startGameButton = createCurvedButton(joinGameCanvas, screenWidth * 0.3, screenHeight * 0.1, bgColour="#5c5c5c", bgColourHover='#7a7a7a', fgColour='#f5f5f5', text='Start Game', bgParent="#24273a", fontSize=30, command=startGame)
        startGameButton.place(relx=0.5, rely=0.925, anchor=CENTER)

        joinGameCanvas.tag_bind("startGameButton", "<Button-1>", lambda event: startGame())
        joinGameCanvas.tag_bind("startGameText", "<Button-1>", lambda event: startGame())

        global joinGameQRCode
        ipAddress = getIPAddress()
        joinGameLink = generateQRCode(f"https://devicesagainsthumanity.bgodfrey.org", "#cad3f5", 5 * scaleWidth)
        joinGameLink = ImageTk.PhotoImage(joinGameLink)
        joinGameQRCode = Label(joinGameCanvas, image=joinGameLink, bg="#8087a2")
        joinGameQRCode.place(relx=0.94, rely=0.9, anchor=CENTER)

        global chooseVoteMethodFrame
        chooseVoteMethodFrame = Frame(welcomeWindow, bg="#24273a")
        chooseVoteMethodFrame.place(relx=0.175, rely=0.925, anchor=CENTER)

        global chooseSingleVoterButton
        chooseSingleVoterButton = createCurvedButton(chooseVoteMethodFrame, screenWidth * 0.15, screenHeight * 0.075, bgColour="#5c5c5c", bgColourHover='#7a7a7a', fgColour='#f5f5f5', text='Single Voter', bgParent="#24273a", fontSize=15, command=lambda: selectVotingMethod('single'))
        chooseSingleVoterButton.pack(side=LEFT, padx=10)

        global chooseMultiVoterButton
        chooseMultiVoterButton = createCurvedButton(chooseVoteMethodFrame, screenWidth * 0.15, screenHeight * 0.075, bgColour="#5c5c5c", bgColourHover='#7a7a7a', fgColour='#f5f5f5', text='Multi Voter', bgParent="#24273a", fontSize=15, command=lambda: selectVotingMethod('multi'))
        chooseMultiVoterButton.pack(side=RIGHT, padx=10)

        global musicToggleButton
        musicToggleButton = createCurvedButton(joinGameCanvas, 0.15 * screenWidth, 0.075 * screenHeight, radius=25, bgColour="#5c5c5c", bgColourHover="#7a7a7a", fgColour="#f5f5f5", text="Music", bgParent="#24273a", fontSize=15, command=lambda: toggleMusicButton())
        musicToggleButton.place(relx=0.775, rely=0.925, anchor=CENTER)

        # Only start notification monitor thread if it's not already running
        global notificationMonitorThread
        if notificationMonitorThread is None or not notificationMonitorThread.is_alive():
            notificationMonitorThread = threading.Thread(target=processNotificationQueue, daemon=True)
            notificationMonitorThread.start()
            log("✅ Started notification monitor thread")

        selectVotingMethod(votingMethod)
        getGameCode()

        # If needed then reads out information about the screen and what the user can do
        if readAloud == 'On':
            readMessage("You are now on the join game screen! Here you can join a game by scanning the QR code or entering the game code. To start the game, click 'Start Game'. To change the voting method, click on 'Single Voter' or 'Multi Voter'.")

        welcomeWindow.mainloop()
    except Exception as e:
        messagebox.showerror("Error building game code window", e)
        exit()

# This function creates the question window. It adds all the necessary labels and buttons
def buildQuestionWindow():
    global joinGameCanvas, questionWindowCanvas, questionContainer, questionLabel, gameCodeLabel, playerCountLabel, timeLeftLabel, countdownLabel, skipCountdownButtonImage, skipQuestionButtonImage, gameInfoContainer, gameCodeLabel, totalPlayersLabel, questionMode

    # Deletes the old canvas's that would be there beforehand and need removing
    try:
        joinGameCanvas.delete("all")
        chooseVoteMethodFrame.destroy()
        joinedUsersFrame.destroy()
        joinGameCanvas.destroy()
    except:
        pass

    try:
        scoreboardCanvas.destroy()
    except:
        pass

    questionWindowCanvas = Canvas(welcomeWindow, width=screenWidth, height=screenHeight, bg="#24273a", highlightthickness=0)
    questionWindowCanvas.place(relwidth=1, relheight=1)

    questionContainer = createCurvedFrame(questionWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="black")
    questionContainer.place(relx=0.1, rely=0.1)

    questionLabel = Label(questionContainer, text="Loading...", font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="black", fg="white", wraplength=screenWidth * 0.25, justify=LEFT)
    questionLabel.place(relx=0.08, rely=0.05, anchor=NW)

    playerCountLabel = questionWindowCanvas.create_text(screenWidth * 0.75, screenHeight * 0.15, text="Players Answered: 0", font=("Arial", int((50 * scaleWidth) * fontScale)), fill="white")

    timeLeftLabel = questionWindowCanvas.create_text(screenWidth * 0.75, screenHeight * 0.225, text="Time Left:", font=("Arial", int((30 * scaleWidth) * fontScale)), fill="white")

    countdownLabel = questionWindowCanvas.create_text(screenWidth * 0.75, screenHeight * 0.5, text="60", font=("Arial", int((500 * scaleWidth) * fontScale)), fill="white")

    skipCountdownButtonImage = questionWindowCanvas.create_image(screenWidth * 0.75, screenHeight * 0.82, image=skipLogo)

    skipQuestionButton = Button(questionContainer, image = skipLogo, bg="black", bd=0, highlightthickness=0, highlightcolor='black', activebackground='black', activeforeground='white', command=requestBlackCard)
    skipQuestionButton.place(relx=0.5, rely=0.9, anchor=CENTER)

    questionWindowCanvas.tag_bind(skipCountdownButtonImage, "<Button-1>", lambda event: skipToVoting())

    gameInfoContainer = Frame(welcomeWindow, bg="black")
    gameInfoContainer.pack(side=BOTTOM, fill=X)
    
    gameCodeLabel = Label(gameInfoContainer, text=f'Game Code: {gameCode}', font=("Arial", int((30 * scaleWidth) * fontScale)), fg = "white", bg = "black")
    gameCodeLabel.pack(side = LEFT, padx=10)
    
    totalPlayersLabel = Label(gameInfoContainer, text=f'Total Players: {len(users)}', font=("Arial", int((30 * scaleWidth) * fontScale)), fg = "white", bg = "black")
    totalPlayersLabel.pack(side = RIGHT, padx=10)

    questionMode = True

# This function creates the voting window. It adds all the necessary labels and buttons
def buildVotingWindow():
    global votingWindowCanvas, votingWindowTitle, votingContainer, votingLabel, playerAnswerContainer, playerAnswerLabel, gameInfoContainer, gameCodeLabel, totalPlayersLabel, questionMode

    # Deletes the old canvas's that would be there beforehand and need removing
    try:
        questionWindowCanvas.delete("all")
        questionWindowCanvas.destroy()
        gameInfoContainer.destroy()
    except:
        pass

    questionMode = False

    votingWindowCanvas = Canvas(welcomeWindow, width=screenWidth, height=screenHeight, bg="#24273a", highlightthickness=0)
    votingWindowCanvas.place(relwidth=1, relheight=1)

    votingWindowTitle = votingWindowCanvas.create_text(screenWidth / 2, screenHeight * 0.08, text='Voting Time!', font=("Arial", int((100 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    votingContainer = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="black")
    votingContainer.place(relx=0.15, rely=0.15)

    votingLabel = Label(votingContainer, text="Loading...", font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="black", fg="white", wraplength=screenWidth * 0.25, justify=LEFT)
    votingLabel.place(relx=0.08, rely=0.05, anchor=NW)

    gameInfoContainer = Frame(welcomeWindow, bg="black")
    gameInfoContainer.pack(side=BOTTOM, fill=X)
    
    gameCodeLabel = Label(gameInfoContainer, text=f'Game Code: {gameCode}', font=("Arial", int((30 * scaleWidth) * fontScale)), fg = "white", bg = "black")
    gameCodeLabel.pack(side = LEFT, padx=10)
    
    totalPlayersLabel = Label(gameInfoContainer, text=f'Total Players: {len(users)}', font=("Arial", int((30 * scaleWidth) * fontScale)), fg = "white", bg = "black")
    totalPlayersLabel.pack(side = RIGHT, padx=10)

    threading.Thread(target=requestAnswers, daemon=True).start()
    while len(answers) == 0:
        pass
    showVotes()

# This function creates the winner window. It adds all the necessary labels and buttons
def buildWinnerWindow(winningCard, winner):

    # Deletes the old canvas's that would be there beforehand and need removing
    try:
        timeLeftLabel.destroy()
        countdownLabel.destroy()
    except:
        pass
    try:
        votingWindowCanvas.itemconfig(playerCountLabel, text="")
        skipCountdownButtonImage.destroy()
    except:
        pass

    votingWindowCanvas.itemconfig(votingWindowTitle, text=f'Winner: {winner}')
    votingContainer.place(relx=0.15, rely=0.15)

    if '|' in winningCard:
        votingContainer.place(relx=0.025, rely=0.15)

        winningCard = winningCard.split('|')

        playerAnswerContainer1 = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
        playerAnswerContainer1.place(relx=0.375, rely=0.15)
        playerAnswerLabel1 = Label(playerAnswerContainer1, text=winningCard[0], font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
        playerAnswerLabel1.place(relx=0.08, rely=0.05, anchor=NW)

        playerAnswerContainer2 = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
        playerAnswerContainer2.place(relx=0.675, rely=0.15)
        playerAnswerLabel2 = Label(playerAnswerContainer2, text=winningCard[1], font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
        playerAnswerLabel2.place(relx=0.08, rely=0.05, anchor=NW)
    else:
        playerAnswerContainer = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
        playerAnswerContainer.place(relx=0.55, rely=0.15)
        playerAnswerLabel = Label(playerAnswerContainer, text=winningCard, font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
        playerAnswerLabel.place(relx=0.08, rely=0.05, anchor=NW)

    # If needed then reads out information about the screen and what the user can do
    if readAloud == 'On':
        readMessage(f"The winner is {winner} with the card {winningCard}. The game will continue in a few seconds")

    time.sleep(5)
    buildScoreboardWindow()

# This function creates the scoreboard window. It adds all the necessary labels and buttons
def buildScoreboardWindow():
    # Deletes the old canvas's that would be there beforehand and need removing
    try:
        votingWindowCanvas.delete("all")
        votingWindowCanvas.destroy()
        gameInfoContainer.destroy()
    except:
        pass

    global scoreboardCanvas, scoreboardTitle, continueLabel, endButton
    scoreboardCanvas = Canvas(welcomeWindow, width=screenWidth, height=screenHeight, bg="#24273a", highlightthickness=0)
    scoreboardCanvas.place(relwidth=1, relheight=1)

    scoreboardTitle = scoreboardCanvas.create_text(screenWidth / 2, screenHeight * 0.1, text='Scoreboard', font=("Arial", int((100 * scaleWidth) * fontScale), 'bold'), fill="#cad3f5")

    roundsLeftLabel = Label(scoreboardCanvas, text=f"Rounds Left: {numOfRounds}", font=("Arial", int((20 * scaleWidth) * fontScale), 'bold'), bg="#24273a", fg="white")
    roundsLeftLabel.place(relx=0.85, rely=0.13, anchor=CENTER)

    continueLabel = Label(scoreboardCanvas, text="Continuing in:", font=("Arial", int((20 * scaleWidth) * fontScale), 'bold'), bg="#24273a", fg="white")
    continueLabel.place(relx=0.85, rely=0.08, anchor=CENTER)

    endButton = createCurvedButton(scoreboardCanvas, int(250 * scaleWidth), int(100 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="End Game", bgParent="#24273a", command=exitGame)
    endButton.place(relx=0.15, rely=0.1, anchor=CENTER)

    threading.Thread(target=requestPlayerScores, daemon=True).start()
    threading.Thread(target=continueCountdown, daemon=True).start()

    threading.Thread(target=changeGameState, args=('scoreboard',), daemon=True).start()

    # If needed then reads out information about the screen and what the user can do
    if readAloud == 'On':
        readMessage(f"This is the scoreboard screen! Here you can see the scores of all the players. At current there are {numOfRounds} rounds left. The game will continue in a few seconds.")

# This function allows the user to skip the countdown and move to the voting stages
def skipToVoting():
    global countdown
    countdown = 0

# This function allows the user to skip the countdown and move to the results stage
def skipToResults():
    global countdown, countdownActive
    countdownActive = False
    countdown = 0
    # Immediately trigger the end of voting
    threading.Thread(target=endVoting, daemon=True).start()

# Add this new function to handle the end of voting
def endVoting():
    global votes, playersAnswered
    if votingMethod == 'multi':
        # If multi-voting and we have votes, determine winner
        if len(votes) > 0:
            playersAnswered = len(users)  # Force it to process results
            winningAnswer = determineWinner(votes)
            temp = winningAnswer.split("|")
            length = len(temp)
            if length == 2:
                winningAnswer = temp[0]
                winningPlayer = temp[1]
            if length == 3:
                winningAnswer = temp[0] + "|" + temp[1]
                winningPlayer = temp[2]
            votes = []
            updatePlayerScore(winningPlayer)
            buildWinnerWindow(winningAnswer, winningPlayer)
        else:
            # No votes received, skip to next round
            buildScoreboardWindow()
    else:
        # For single voting, if no vote received, skip to next round
        buildScoreboardWindow()

# This function finds all the card packs in the database and returns them
def findCardPacks(source=None):
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")    
    tables = [table[0] for table in c.fetchall()]

    if 'sqlite_sequence' in tables:
        tables.remove('sqlite_sequence')

    # If the source is the create game window, then it retrieves a list of the card packs on the server
    if source == 'createGameWindow':
        try:
            request = requests.get(f"{base_url}/getCardPacks")
            cardPacks = request.json()

            for cardPack in cardPacks['cardPacks']:
                if cardPack not in tables:
                    tables.append(cardPack)
        except Exception as e:
            messagebox.showerror("Error getting card packs", e)

    return tables  

# This function fills a canvas with the black card packs
def fillBlackCardsTable(blackCardPacks):
    global min, max, tempButtonsBlack
    try:
        for button in tempButtonsBlack:
            button.destroy()
    except:
        pass

    blackrow = 0.05
    for card in blackCardPacks[min:max]:
        if card in selectedCardPacks:
            card = card[1:]
            tempButton = createCurvedButton(blackCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="green", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text=card)
        else:
            card = card[1:]
            tempButton = createCurvedButton(blackCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text=card)
        tempButton.bind("<Button-1>", lambda event, card=card, tempButton=tempButton: selectCardPack(tempButton, '0' + str(card)))
        tempButton.place(relx=0.05, rely=blackrow, relwidth=0.9, relheight=0.1)
        tempButtonsBlack.append(tempButton)
        blackrow += 0.1

# This function fills a canvas with the white card packs
def fillWhiteCardsTable(whiteCardPacks):
    global min, max, tempButtonsWhite
    try:
        for button in tempButtonsWhite:
            button.destroy()
    except:
        pass
    whiterow = 0.05
    for card in whiteCardPacks[min:max]:
        if card in selectedCardPacks:
            card = card[1:]
            tempButton = createCurvedButton(whiteCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="green", bgColourHover="#5c5c5c", fgColour="black", bgParent='#8087a2', text=card)
        else:
            card = card[1:]
            tempButton = createCurvedButton(whiteCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="white", bgColourHover="#5c5c5c", fgColour="black", bgParent='#8087a2', text=card)
        tempButton.bind("<Button-1>", lambda event, card=card, tempButton=tempButton: selectCardPack(tempButton, '1' + str(card)))
        tempButton.place(relx=0.05, rely=whiterow, relwidth=0.9, relheight=0.1)
        tempButtonsWhite.append(tempButton)
        whiterow += 0.1

# This function fills a canvas with the existing card packs
def fillExisitingCardsTable(tables):
    try:
        for button in tempButtons:
            button.destroy()
    except:
        pass
    if len(tables) !=0:
        preExistingCardPacksLabel.destroy()
        row = 0.05
        for table in tables[min:max]:
            cardPackType = str(table[0])
            table = table[1:]
            if cardPackType == '0':
                tempButton = createCurvedButton(preExistingCardPacksCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", bgParent='#8087a2', text=table)
                tempButton.bind("<Button-1>", lambda event, table=table: buildEditCardPackWindow('0' + str(table)))
            else:
                tempButton = createCurvedButton(preExistingCardPacksCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="white", bgColourHover="#5c5c5c", fgColour="black", bgParent='#8087a2', text=table)
                tempButton.bind("<Button-1>", lambda event, table=table: buildEditCardPackWindow('1' + str(table)))
            tempButton.place(relx=0.05, rely=row, relwidth=0.9, relheight=0.1)
            tempButtons.append(tempButton)
            row += 0.1

# This function fills a canvas with the existing cards in a card pack
def fillInExistingCards(cardPackType, cardPackName):
    global preExistingCardsNoCardsLabel, cardButtons, min, max
    if cardPackType == '0':
        try:
            c.execute(f"SELECT question FROM '{cardPackName}'")
            cards = c.fetchall()
            temp = []
            for card in cards:
                temp.append(card[0])
            cards = temp
        except:
            messagebox.showerror("Error fetching cards from card pack")
    if cardPackType == '1':
        try:
            c.execute(f"SELECT answer FROM '{cardPackName}'")
            cards = c.fetchall()
            temp = []
            for card in cards:
                temp.append(card[0])
            cards = temp
        except:
            messagebox.showerror("Error fetching cards from card pack")  

    try:
        for button in cardButtons:
            button.destroy()
    except:
        pass

    if len(cards) == 0:
        preExistingCardsNoCardsLabel = Label(preExistingCardsCanvas, text="No cards in this pack yet", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
        preExistingCardsNoCardsLabel.place(relx=0.5, rely=0.5, anchor=CENTER)
        return
    else:
        try:
            preExistingCardsNoCardsLabel.destroy()
        except:
            pass

    row = 0.05
    for card in cards[min:max]:
        if cardPackType == '0':
            cardButton = createCurvedButton(preExistingCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text=card, bgParent="#8087a2", command=lambda cardPackType=cardPackType, cardPackName=cardPackName, card=card: editCardPopup(cardPackType, cardPackName, card))
        if cardPackType == '1':
            cardButton = createCurvedButton(preExistingCardsCanvas, int(690 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="white", bgColourHover="#5c5c5c", fgColour="black", text=card, bgParent="#8087a2", command=lambda cardPackType=cardPackType, cardPackName=cardPackName, card=card: editCardPopup(cardPackType, cardPackName, card))
        cardButton.place(relx=0.05, rely=row, relwidth=0.9, relheight=0.1)
        cardButtons.append(cardButton)
        row += 0.1

# This function adds a blank space ('_____') to the black card question entry box
def insertAnswerSpace():
    global newCardQuestionEntry
    question = newCardQuestionEntry.get()
    count = question.count("_____")
    if count < 2:
        newCardQuestionEntry.delete(0, END)
        newCardQuestionEntry.insert(0, question + "_____")
        count += 1
    else:
        successOrErrorLabel.config(text="Question already contains max answer spaces", fg="red")
        if readAloud == 'On':
            readMessage("Question already contains max answer spaces")
    if count == 1:
        setAnswerCount(1)
    if count == 2:
        setAnswerCount(2)

# This function changes the number of required answers for a black card when creating it
def setAnswerCount(number):
    global answerCount
    answerCount = number
    if number == 1:
        changeCurvedButtonColour(answerCount1Button, answerCount1Button.label_id, "green")
        changeCurvedButtonColour(answerCount2Button, answerCount2Button.label_id, "black")
        unbindCurvedButton(answerCount1Button, answerCount1Button.label_id)
        rebindCurvedButton(answerCount2Button, answerCount2Button.label_id, "black", "green")
    if number == 2:
        changeCurvedButtonColour(answerCount2Button, answerCount2Button.label_id, "green")
        changeCurvedButtonColour(answerCount1Button, answerCount1Button.label_id, "black")
        unbindCurvedButton(answerCount2Button, answerCount2Button.label_id)
        rebindCurvedButton(answerCount1Button, answerCount1Button.label_id, "black", "green")

# This function creates a new card pack in the database
def createNewCardPack(name, cardType):
    try:
        name = name.replace(" ", "")
        name = re.sub(r'\W+', '', name)
        if cardType == 'black':
            name = '0' + name
            c.execute(f"CREATE TABLE '{name}' (ID INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answerNum INTEGER)")
            conn.commit()
        else:
            name = '1' + name
            c.execute(f"CREATE TABLE '{name}' (ID INTEGER PRIMARY KEY AUTOINCREMENT, answer TEXT)")
            conn.commit()
    except Exception as e:
        messagebox.showerror("Error creating new card pack", e)

    buildEditCardPackWindow(name)

# This function deletes a card pack from the database
def deleteCardPack(cardPackName):
    try:
        c.execute(f"DROP TABLE '{cardPackName}'")
        conn.commit()
        buildCardPackWindow()
    except Exception as e:
        messagebox.showerror("Error deleting card pack", e)

# This function marks the card packs as selected when selecting the card packs to use in a game
def selectCardPack(button, card):
    global createGameWindowCanvas, backButton, pageTitle, blackCardsCanvas, whiteCardsCanvas, selectedCardPacks
    if card in selectedCardPacks:
        cardType = card[0]
        selectedCardPacks.remove(card)
        if cardType == '0':
            changeCurvedButtonColour(button, button.label_id, 'black')
            unbindCurvedButton(button, button.label_id)
            rebindCurvedButton(button, button.label_id, 'black', 'grey')
        else:
            changeCurvedButtonColour(button, button.label_id, 'white')
            unbindCurvedButton(button, button.label_id)
            rebindCurvedButton(button, button.label_id, 'white', 'grey')
    else:
        selectedCardPacks.append(card)
        changeCurvedButtonColour(button, button.label_id, 'green')
        unbindCurvedButton(button, button.label_id)
        rebindCurvedButton(button, button.label_id, 'green', 'grey')

# This function gets all the cards in a card pack
def getCards(cardPackName, cardPackType):
    temp = []
    try:
        if cardPackType == '0':
            c.execute(f"SELECT question FROM '{cardPackName}'")
        if cardPackType == '1':
            c.execute(f"SELECT answer FROM '{cardPackName}'")
        cards = c.fetchall()
    except Exception as e:
        messagebox.showerror("Error fetching cards from card pack", e)

    for card in cards:
        temp.append(card[0])
    cards = temp

    return cards

# This function adds new card to the card pack
def addNewCard(cardPackType, cardPackName, question=None, answer=None, answerNum=None):
    global max, answerCount
    success = False

    cards = getCards(cardPackName, cardPackType)
    if maxCardPackSize != 'Unlimited':
        if len(cards) == int(maxCardPackSize):
            successOrErrorLabel.config(text="Card pack is full", fg="red")
            if readAloud == 'On':
                readMessage("Card pack is full")
            return

    if cardPackType == '0' and question and answerNum:
        if answerNum.isnumeric():
            c.execute(f"SELECT question FROM '{cardPackName}' WHERE question = ?", (question,))
            if c.fetchone() is not None:
                successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
                if readAloud == 'On':
                    readMessage("Card already exists in card pack")
            else:
                c.execute(f"INSERT INTO '{cardPackName}' (question, answerNum) VALUES (?, ?)", (question, int(answerNum),))
                conn.commit()
                success = True
        else:
            successOrErrorLabel.config(text="Please select the number of answers required", fg="red")
            if readAloud == 'On':
                readMessage("Please select the number of answers required")
    elif cardPackType == '1' and answer:
        c.execute(f"SELECT answer FROM '{cardPackName}' WHERE answer = ?", (answer,))
        if c.fetchone() is not None:
            successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
            if readAloud == 'On':
                readMessage("Card already exists in card pack")
        else:
            c.execute(f"INSERT INTO '{cardPackName}' (answer) VALUES (?)", (answer,))
            conn.commit()
            success = True

    if success:
        if cardPackType == '0':
            newCardQuestionEntry.delete(0, END)
            changeCurvedButtonColour(answerCount1Button, answerCount1Button.label_id, "black")
            changeCurvedButtonColour(answerCount2Button, answerCount2Button.label_id, "black")
            answerCount = None
        elif cardPackType == '1':
            newCardAnswerEntry.delete(0, END)
        
        successOrErrorLabel.config(text="Card added successfully", fg="green")
        if readAloud == 'On':
            readMessage("Card added successfully")
        max += 1
        fillInExistingCards(cardPackType, cardPackName)

# This function updates the card in the card pack with requested changes
def updateCard(cardPackType, cardPackName, oldCard, newCard, newAnswerNum=None):
    try:
        if cardPackType == '0':
            c.execute(f"SELECT question FROM '{cardPackName}' WHERE question = ?", (newCard,))
            if c.fetchone() is not None:
                successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
                if readAloud == 'On':
                    readMessage("Card already exists in card pack")
                editCardCanvas.destroy()
                return
            if newAnswerNum and newAnswerNum.isnumeric():
                c.execute(f"UPDATE '{cardPackName}' SET question = ?, answerNum = ? WHERE question = ?", (newCard, int(newAnswerNum), oldCard))
                conn.commit()
                successOrErrorLabel.config(text="Card updated successfully", fg="green")
                if readAloud == 'On':
                    readMessage("Card updated successfully")
            else:
                successOrErrorLabel.config(text="Number of answers must be an integer", fg="red")
                if readAloud == 'On':
                    readMessage("Number of answers must be an integer")
        elif cardPackType == '1':
            c.execute(f"SELECT answer FROM '{cardPackName}' WHERE answer = ?", (newCard,))
            if c.fetchone() is not None:
                successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
                if readAloud == 'On':
                    readMessage("Card already exists in card pack")
                editCardCanvas.destroy()
                return
            c.execute(f"UPDATE '{cardPackName}' SET answer = ? WHERE answer = ?", (newCard, oldCard))
            conn.commit()
            successOrErrorLabel.config(text="Card updated successfully", fg="green")
            if readAloud == 'On':
                readMessage("Card updated successfully")
        editCardCanvas.destroy()
        fillInExistingCards(cardPackType, cardPackName)

    except Exception as e:
        successOrErrorLabel.config(text=f"Error updating card: {e}", fg="red")
        if readAloud == 'On':
            readMessage(f"There was an error updating the card")
        editCardCanvas.destroy()

# This function removes the requested card from the card pack
def deleteCard(cardPackType, cardPackName, card):
    global max
    if cardPackType == '0':
        c.execute(f"DELETE FROM '{cardPackName}' WHERE question = ?", (card,))
        conn.commit()
        successOrErrorLabel.config(text="Card deleted successfully", fg="green")
        if readAloud == 'On':
            readMessage("Card deleted successfully")
        editCardCanvas.destroy()
        max -= 1
        fillInExistingCards(cardPackType, cardPackName)
    if cardPackType == '1':
        c.execute(f"DELETE FROM '{cardPackName}' WHERE answer = ?", (card,))
        conn.commit()
        successOrErrorLabel.config(text="Card deleted successfully", fg="green")
        if readAloud == 'On':
            readMessage("Card deleted successfully")
        editCardCanvas.destroy()
        max -= 1
        fillInExistingCards(cardPackType, cardPackName)

# This function builds the GUI for moving the card to the desired card pack
def moveCard(cardPackType, cardPackName, card):
    global moveCardPackCanvas
    moveCardPackCanvas = createCurvedFrame(editCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    moveCardPackCanvas.place(relx=0.54, rely=0.16)

    moveCardLabel = Label(moveCardPackCanvas, text="Move Card", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea")
    moveCardLabel.place(relx=0.5, rely=0.1, anchor=CENTER)

    cardBeingMovedLabel = Label(moveCardPackCanvas, text=f"Card: {card}", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
    cardBeingMovedLabel.place(relx=0.5, rely=0.3, anchor=CENTER)

    moveCardQuestionLabel = Label(moveCardPackCanvas, text="Move to card pack", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea")
    moveCardQuestionLabel.place(relx=0.5, rely=0.4, anchor=CENTER)

    cardPacks = findCardPacks()
    cardPacks.remove(cardPackName)
    
    if cardPackType == '0':
        for cardPack in cardPacks:
            if cardPack[0] != '0':
                cardPacks.remove(cardPack)

    if cardPackType == '1':
        for cardPack in cardPacks:
            if cardPack[0] != '1':
                cardPacks.remove(cardPack)

    for cardPack in cardPacks:
        if cardPack[0] == '0':
            cardPacks[cardPacks.index(cardPack)] = cardPack[1:]
        if cardPack[0] == '1':
            cardPacks[cardPacks.index(cardPack)] = cardPack[1:]

    moveCardQuestionMulti = ttk.Combobox(moveCardPackCanvas, values=cardPacks, font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)))
    moveCardQuestionMulti.place(relx=0.5, rely=0.45, anchor=CENTER)

    buttonContainer = Frame(moveCardPackCanvas, bg="#8087a2")
    buttonContainer.place(relx=0.5, rely=0.7, anchor=CENTER)

    moveCardSaveButton = createCurvedButton(buttonContainer, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Move", bgParent="#8087a2", command=lambda: moveCardToPack(cardPackType, cardPackName, card, moveCardQuestionMulti.get()))
    moveCardSaveButton.pack(side=RIGHT, padx=10)

    cancelCardButton = createCurvedButton(buttonContainer, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Cancel", bgParent="#8087a2", command=lambda: moveCardPackCanvas.destroy())
    cancelCardButton.pack(side=LEFT, padx=10)

# This function moves the card to the desired card pack
def moveCardToPack(cardPackType, cardPackName, card, newCardPack):
    global max
    newCardPack = cardPackType + newCardPack
    try:
        if cardPackType == '0':
            c.execute(f"SELECT question FROM '{newCardPack}' WHERE question = ?", (card,))
            if c.fetchone() is not None:
                successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
                if readAloud == 'On':
                    readMessage("Card already exists in card pack")
                moveCardPackCanvas.destroy()
                editCardCanvas.destroy()
                return
            c.execute(f"SELECT question, answerNum FROM '{cardPackName}' WHERE question = ?", (card,))
            data = c.fetchone()
            c.execute(f"INSERT INTO '{newCardPack}' (question, answerNum) VALUES (?, ?)", (data[0], data[1],))
            c.execute(f"DELETE FROM '{cardPackName}' WHERE question = ?", (card,))
            conn.commit()
            successOrErrorLabel.config(text="Card moved successfully", fg="green")
            if readAloud == 'On':
                readMessage("Card moved successfully")
            moveCardPackCanvas.destroy()
            editCardCanvas.destroy()
            fillInExistingCards(cardPackType, cardPackName)
        elif cardPackType == '1':
            c.execute(f"SELECT answer FROM '{newCardPack}' WHERE answer = ?", (card,))
            if c.fetchone() is not None:
                successOrErrorLabel.config(text="Card already exists in card pack", fg="red")
                if readAloud == 'On':
                    readMessage("Card already exists in card pack")
                moveCardPackCanvas.destroy()
                editCardCanvas.destroy()
                return
            c.execute(f"SELECT answer FROM '{cardPackName}' WHERE answer = ?", (card,))
            data = c.fetchone()
            c.execute(f"INSERT INTO '{newCardPack}' (answer) VALUES (?)", (data[0],))
            c.execute(f"DELETE FROM '{cardPackName}' WHERE answer = ?", (card,))
            conn.commit()
            successOrErrorLabel.config(text="Card moved successfully", fg="green")
            if readAloud == 'On':
                readMessage("Card moved successfully")
            moveCardPackCanvas.destroy()
            editCardCanvas.destroy()
            max -= 1
            fillInExistingCards(cardPackType, cardPackName)
    except Exception as e:
        successOrErrorLabel.config(text=f"Error moving card: {e}", fg="red")
        if readAloud == 'On':
            readMessage(f"There was an error moving the card")
        moveCardPackCanvas.destroy()

# This function creates the screen for editing the card in a card pack
def editCardPopup(cardPackType, cardPackName, card):
    global editCardPackCanvas, newCardCanvas, editCardCanvas
    editCardCanvas = createCurvedFrame(editCardPackCanvas, screenWidth * 0.4, screenHeight * 0.7, radius=25, bg_colour="#8087a2")
    editCardCanvas.place(relx=0.54, rely=0.16)

    if cardPackType == '0':
        editCardLabel = Label(editCardCanvas, text="Edit Card", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea")
        editCardLabel.place(relx=0.5, rely=0.1, anchor=CENTER)

        editCardQuestionLabel = Label(editCardCanvas, text="Contents", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
        editCardQuestionLabel.place(relx=0.5, rely=0.3, anchor=CENTER)

        editCardQuestionEntry = Entry(editCardCanvas, font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)))
        editCardQuestionEntry.place(relx=0.5, rely=0.35, anchor=CENTER)

        editCardQuestionAnswerCountLabel = Label(editCardCanvas, text="Number of answers", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
        editCardQuestionAnswerCountLabel.place(relx=0.5, rely=0.5, anchor=CENTER)

        editCardQuestionAnswerCountEntry = Entry(editCardCanvas, font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)))
        editCardQuestionAnswerCountEntry.place(relx=0.5, rely=0.55, anchor=CENTER)

    if cardPackType == '1':
        editCardLabel = Label(editCardCanvas, text="Edit Card", font=("Helvetica Neue", int((30 * scaleWidth) * fontScale), 'bold'), bg="#8087a2", fg="#eaeaea")
        editCardLabel.place(relx=0.5, rely=0.1, anchor=CENTER)

        global editCardAnswerLabel
        editCardAnswerLabel = Label(editCardCanvas, text="Contents", font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)), bg="#8087a2", fg="#eaeaea")
        editCardAnswerLabel.place(relx=0.5, rely=0.4, anchor=CENTER)

        global editCardAnswerEntry
        editCardAnswerEntry = Entry(editCardCanvas, font=("Helvetica Neue", int((20 * scaleWidth) * fontScale)))
        editCardAnswerEntry.place(relx=0.5, rely=0.45, anchor=CENTER)

    editCardSaveButton = createCurvedButton(editCardCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Save", bgParent="#8087a2", command=lambda: updateCard(cardPackType, cardPackName, card, editCardQuestionEntry.get() if cardPackType == '0' else editCardAnswerEntry.get(), editCardQuestionAnswerCountEntry.get() if cardPackType == '0' else None))
    editCardSaveButton.place(relx=0.5, rely=0.7, anchor=CENTER)

    deleteCardButton = createCurvedButton(editCardCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Delete", bgParent="#8087a2", command=lambda: deleteCard(cardPackType, cardPackName, card))
    deleteCardButton.place(relx=0.15, rely=0.93, anchor=CENTER)

    cancelCardButton = createCurvedButton(editCardCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Cancel", bgParent="#8087a2", command=lambda: editCardCanvas.destroy())
    cancelCardButton.place(relx=0.5, rely=0.93, anchor=CENTER)

    moveCardButton = createCurvedButton(editCardCanvas, int(200 * scaleWidth), int(75 * scaleHeight), radius=25, bgColour="black", bgColourHover="#5c5c5c", fgColour="white", text="Move", bgParent="#8087a2", command=lambda: moveCard(cardPackType, cardPackName, card))
    moveCardButton.place(relx=0.85, rely=0.93, anchor=CENTER)

    if cardPackType == '0':
        c.execute(f"SELECT answerNum FROM '{cardPackName}' WHERE question = ?", (card,))
        answerNum = c.fetchone()[0]
        editCardQuestionEntry.insert(0, card)
        editCardQuestionAnswerCountEntry.insert(0, answerNum)

    if cardPackType == '1':
        editCardAnswerEntry.insert(0, card)

    if readAloud == 'On':
        readMessage("This is the edit card screen. Here you can edit the card, delete it, or move it to another card pack.")

# This function grabs all the cards and sends each card to the backend server to be processed
def uploadCustomCardPack(requestedPack):
    c.execute(f"SELECT * FROM '{requestedPack}'")
    cards = c.fetchall()
    # split each card into its id, question/answer, and answerNum
    for card in cards:
        cardID = card[0]
        cardText = card[1]
        if requestedPack[0] == '0':
            answerNum = card[2]
            data = f"command: uploadCard, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, cardType: black, cardID: {cardID}, cardText: {cardText}, answerNum: {answerNum}"
        else:
            data = f"command: uploadCard, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, cardType: white, cardID: {cardID}, cardText: {cardText}"
        threading.Thread(target=sendMessageToServer, args=(data,), daemon=True).start()

# Safe wrapper for transferCardPacks to handle GUI cleanup
def safeTransferCardPacks(selectedCardPacks):
    try:
        transferCardPacks(selectedCardPacks)
    except Exception as e:
        log(f"Error in transferCardPacks: {e}")

# This function tells the server what card packs are being used.
def transferCardPacks(selectedCardPacks):
    try:
        # Wait for WebSocket connection with timeout
        timeout_counter = 0
        while websocketConnected != True and timeout_counter < 30:
            time.sleep(0.1)
            timeout_counter += 1
        
        # If still not connected after timeout, exit
        if not websocketConnected:
            log("WebSocket connection timeout in transferCardPacks")
            return
        
        # Check if userLabel still exists before trying to update it
        try:
            if 'userLabel' in globals() and userLabel.winfo_exists():
                userLabel.config(text="Syncing with server...")
        except Exception:
            # Widget no longer exists or is invalid, skip GUI update
            pass
        
        addNotification("Transferring card packs")
        temp = ''
        for i in range(len(selectedCardPacks)):
            temp += selectedCardPacks[i]
            if i != len(selectedCardPacks) - 1:
                temp += ','
        
        try:
            data = f"command: transferCardPacks, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, cardPacks: {temp}"
            sendMessageToServer(data)
        except Exception as e:
            log(f"Error transferring card packs: {e}")
            
    except Exception as e:
        log(f"Error in transferCardPacks thread: {e}")

# This function updates the displayed users on the join game screen when users join or leave
def updateDisplayedUsers():
    # Safely update the join-game users display only if the frame/widget exists
    try:
        if 'joinedUsersFrame' not in globals() or joinedUsersFrame is None:
            return
        # joinedUsersFrame may have been destroyed; check existence
        try:
            if not getattr(joinedUsersFrame, 'winfo_exists', lambda: False)():
                return
        except Exception:
            # If winfo_exists itself errors, bail out
            return

        # Clear previous user labels to avoid overlapping
        for widget in joinedUsersFrame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        # Display updated list of users
        x, y = 0, 0  # Reset grid position for each new render
        for user in users:
            try:
                userLabel = Label(joinedUsersFrame, text=user, font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#24273a", fg="#cad3f5")
                userLabel.grid(row=y, column=x, padx=20, pady=20)
                if x == 4:
                    x = 0
                    y += 1
                else:
                    x += 1
            except Exception:
                # Skip labels that fail to create (frame may have been destroyed mid-loop)
                continue
    except Exception as e:
        # Log the error but avoid showing GUI error popups here
        log(f"Error updating displayed users: {e}")

# This function changes the selected voting method for the game
def selectVotingMethod(method):
    global chooseSingleVoterButton, chooseMultiVoterButton, votingMethod
    if method == 'single':
        votingMethod = 'single'
        changeCurvedButtonColour(chooseSingleVoterButton, chooseSingleVoterButton.label_id, "green")
        changeCurvedButtonColour(chooseMultiVoterButton, chooseMultiVoterButton.label_id, "#5c5c5c")
        unbindCurvedButton(chooseSingleVoterButton, chooseSingleVoterButton.label_id)
        rebindCurvedButton(chooseMultiVoterButton, chooseMultiVoterButton.label_id, "#5c5c5c", "#7a7a7a")
    if method == 'multi':
        votingMethod = 'multi'
        changeCurvedButtonColour(chooseSingleVoterButton, chooseSingleVoterButton.label_id, "#5c5c5c")
        changeCurvedButtonColour(chooseMultiVoterButton, chooseMultiVoterButton.label_id, "green")
        unbindCurvedButton(chooseMultiVoterButton, chooseMultiVoterButton.label_id)
        rebindCurvedButton(chooseSingleVoterButton, chooseSingleVoterButton.label_id, "#5c5c5c", "#7a7a7a")

def toggleMusicButton(option = 'toggle'):
    global _audio_state, musicToggleButton
    if option == 'toggle':
        if _audio_state == 'playing':
            streamAudio(state = 'stop')
            changeCurvedButtonColour(musicToggleButton, musicToggleButton.label_id, "red")
            unbindCurvedButton(musicToggleButton, musicToggleButton.label_id)
            rebindCurvedButton(musicToggleButton, musicToggleButton.label_id, "red", "green")
        else:
            streamAudio(state = 'play')
            changeCurvedButtonColour(musicToggleButton, musicToggleButton.label_id, "green")
            unbindCurvedButton(musicToggleButton, musicToggleButton.label_id)
            rebindCurvedButton(musicToggleButton, musicToggleButton.label_id, "green", "red")
    if option == 'on':
        changeCurvedButtonColour(musicToggleButton, musicToggleButton.label_id, "green")
        unbindCurvedButton(musicToggleButton, musicToggleButton.label_id)
        rebindCurvedButton(musicToggleButton, musicToggleButton.label_id, "green", "red")
    if option == 'off':
        changeCurvedButtonColour(musicToggleButton, musicToggleButton.label_id, "red")
        unbindCurvedButton(musicToggleButton, musicToggleButton.label_id)
        rebindCurvedButton(musicToggleButton, musicToggleButton.label_id, "red", "green")

# This function checks that the requirements to start the game are met and then begins the game setup
def startGame():
    if len(users) < 3:
        if readAloud == 'On':
            readMessage("Need at least 3 players to start the game")
        messagebox.showerror("Insufficient Players", "Need at least 3 players to start game")
        return

    loading = threading.Thread(target=loadingAnimation)
    loading.start()

    gameStartThread = threading.Thread(target=runGameSetup)
    gameStartThread.start()

# This function begins the game setup by taking in the required settings and then building the correct windows and requesting the black card from the backend server
def runGameSetup():
    global selectedUser, selected, roundNumber, numOfRounds

    if numOfRounds != '0' or numOfRounds == 'Unlimited':
        if numOfRounds != 'Unlimited':
            numOfRounds = str(int(numOfRounds) - 1)
        if roundNumber != 0 and votingMethod == 'single':
            try:
                data = f"command: selectVoter, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, selectedUser: {selectedUser}"
                sendMessageToServer(data)
            except Exception as e:
                messagebox.showerror("Error selecting voter", e)
            
            selected += 1
            if selected == len(users):
                selected = 0

        if votingMethod == 'single':
            selectedUser = users[selected]
            roundNumber += 1
            try:
                data = f"command: selectVoter, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, selectedUser: {selectedUser}"
                sendMessageToServer(data)
            except Exception as e:
                messagebox.showerror("Error selecting voter", e)

        if readAloud == 'On':
            readMessage("Game starting")

        global gameWindowThread
        gameWindowThread = threading.Thread(target=buildQuestionWindow)
        gameWindowThread.start()
        gameWindowThread.join()

        try:
            requestBlackCard()
        except Exception as e:
            messagebox.showerror("Error getting black card", e)
    else:
        exitGame()

# This function begins the countdown and adjusts the onscreen timer
def startCountdown(source, timer=60):
    global countdownLabel
    global countdown
    global countdownActive

    if countdownActive == True:
        countdownActive = False
        time.sleep(0.1)

    countdownActive = True
    countdown = timer + 1
    while countdown > 0 and countdownActive == True:
        countdown -= 1

        if countdown == timer/2:
            if readAloud == 'On':
                readMessage("Halfway through the countdown")

        if source == 'questionWindowCanvas':
            questionWindowCanvas.itemconfig(countdownLabel, text=str(countdown))
        elif source == 'votingWindowCanvas':
            votingWindowCanvas.itemconfig(countdownLabel, text=str(countdown))
        
        # Change color to red if countdown is less than or equal to 15
        if countdown <= 15:
            color = "red"
            if readAloud == 'On':
                readMessage(str(countdown))
        else:
            color = "white"
        
        if source == 'questionWindowCanvas':
            questionWindowCanvas.itemconfig(countdownLabel, fill=color)
        elif source == 'votingWindowCanvas':
            votingWindowCanvas.itemconfig(countdownLabel, fill=color)
        
        time.sleep(1)

    if countdownActive == False:
        return
    
    countdownActive = False
    if countdown == 0:
        if source == 'questionWindowCanvas':
            buildVotingWindow()
        elif source == 'votingWindowCanvas':
            pass

# This function changes the countdown of the continue label on the scoreboard page
def continueCountdown():
    global continueButton
    y = 10
    for i in range(10):
        if continueGame == True:
            continueLabel.config(text = f"Continuing in {y}")
            y -= 1
            time.sleep(1)
        else:
            break
    if continueGame == True:
        # Don't unset voter here - let runGameSetup handle it
        runGameSetup()

# This function requests a black card from the server
def requestBlackCard():
    global currentQuestion
    currentQuestion = ''
    try:
        data = f"command: getBlackCard, gameCode: {gameCode}, deviceID: {clientID}, agentType: host"
        sendMessageToServer(data)
    except Exception as e:
        messagebox.showerror("Error getting black card", e)

# This function inserts the received black card from the server into the game
def insertBlackCard(question):
    global currentQuestion, questionWindowCanvas, questionLabel, questionMode, questionCountdown, countdownActive, numBlanks, countdown
    currentQuestion = question

    while not questionMode:
        time.sleep(0.1)

    questionLabel.config(text=question)
    if countdownActive == True:
        countdown = questionCountdown

    if readAloud == 'On' or readCardsOut == 'On':
        readMessage(question)
    
    if countdownActive == False:
        threading.Thread(target=startCountdown, args=("questionWindowCanvas", questionCountdown), daemon=True).start()
        
    numBlanks = question.count('_____')
    if numBlanks == 0:
        numBlanks = 1

    threading.Thread(target=changeGameState, args=("playing", numBlanks), daemon=True).start()

    try:
        endLoadingAnimation()
    except Exception as e:
        messagebox.showerror("Error ending loading animation", e)

# This function updates the number of players that have answered label on the question and voting window
def updateAnswerCount():
    global playersAnswered, playerCountLabel, joinGameCanvas, countdown, votingMethod
    playersAnswered += 1
    questionWindowCanvas.itemconfig(playerCountLabel, text=f"Players Answered: {playersAnswered}")
    if votingMethod == 'single':
        requiredAnswers = len(users) - 1
    else:
        requiredAnswers = len(users)
    if playersAnswered == requiredAnswers:
        countdown = 0
        questionWindowCanvas.itemconfig(countdownLabel, text="0")

# This function requests for the players answers from the backend server when moving to voting
def requestAnswers():
    try:
        data = f"command: getAnswers, gameCode: {gameCode}, deviceID: {clientID}, agentType: host"
        sendMessageToServer(data)
    except Exception as e:
        messagebox.showerror("Error requesting answers", e)

# This function inserts the received answers from the server and formats them ready for display
def insertAnswers(receivedAnswers):
    global answers
    answers = []
    receivedAnswers = receivedAnswers.split(",")
    answers = receivedAnswers
    for i in range(len(answers)):
        answers[i] = answers[i].replace("[", "")
        answers[i] = answers[i].replace("]", "")
        answers[i] = answers[i].replace('"', "")

# This function cycles through the players answers and displays them on the voting window
def showVotes():
    global votingLabel, playerAnswerLabel, answers, currentQuestion, playersAnswered, playerAnswerContainer, playerAnswerContainer1, playerAnswerContainer2, playerAnswerLabel1, playerAnswerLabel2

    votingLabel.config(text=currentQuestion)

    if int(playersAnswered) == 0:
        # Reset container position and cleanup
        votingContainer.place(relx=0.15, rely=0.15)
        complete_cleanup_voting_elements()
        
        playerAnswerContainer = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
        playerAnswerContainer.place(relx=0.55, rely=0.15)
        playerAnswerLabel = Label(playerAnswerContainer, text='No players answered', font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
        playerAnswerLabel.place(relx=0.08, rely=0.05, anchor=NW)
        playersAnswered = 0
        time.sleep(2)
        gameInfoContainer.destroy()
        gameWindowThread = threading.Thread(target=buildQuestionWindow)
        gameWindowThread.start()
        requestBlackCard()
        return

    # COMPLETE cleanup before starting new round
    complete_cleanup_voting_elements()
    
    # Force a small delay to ensure cleanup is complete
    votingWindowCanvas.update()
    time.sleep(0.1)
    
    # Reset voting container to default position
    votingContainer.place(relx=0.15, rely=0.15)
    
    # Reset playersAnswered counter
    playersAnswered = 0
    
    # Shuffle answers for this round
    random.shuffle(answers)
    
    # Process each answer with complete cleanup between each
    for i in range(len(answers)):
        # Complete cleanup before showing each answer
        complete_cleanup_voting_elements()
        
        # Force GUI update after cleanup
        votingWindowCanvas.update()
        
        # Determine layout and position based on current answer
        if '|' in answers[i]:
            # 2-card layout
            votingContainer.place(relx=0.025, rely=0.15)
            display_two_card_answer(answers[i])
        else:
            # 1-card layout
            votingContainer.place(relx=0.15, rely=0.15)
            display_one_card_answer(answers[i])
        
        # Force GUI update after displaying
        votingWindowCanvas.update()
        
        # Wait for TTS to finish if it's playing
        if readAloud == 'On' or readCardsOut == 'On':
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        
        # Then wait additional 2 seconds before moving to next card
        time.sleep(2)
    
    # Final cleanup before voting begins
    complete_cleanup_voting_elements()
    beginVoting()

def complete_cleanup_voting_elements():
    """Complete cleanup function that ensures all voting display elements are properly destroyed"""
    global playerAnswerContainer, playerAnswerLabel, playerAnswerContainer1, playerAnswerLabel1, playerAnswerContainer2, playerAnswerLabel2
    
    # List of all possible voting elements
    cleanup_list = [
        'playerAnswerContainer', 'playerAnswerLabel',
        'playerAnswerContainer1', 'playerAnswerLabel1', 
        'playerAnswerContainer2', 'playerAnswerLabel2'
    ]
    
    # Destroy all elements and reset globals
    for element_name in cleanup_list:
        try:
            element = globals().get(element_name)
            if element is not None:
                if hasattr(element, 'destroy'):
                    element.destroy()
                if hasattr(element, 'place_forget'):
                    element.place_forget()
                # Reset the global variable to None
                globals()[element_name] = None
        except Exception:
            # Even if destruction fails, reset the global
            globals()[element_name] = None
    
    # Force garbage collection of any remaining references
    import gc
    gc.collect()

def display_two_card_answer(answer):
    """Helper function to display a two-card answer with proper cleanup first"""
    global playerAnswerContainer1, playerAnswerLabel1, playerAnswerContainer2, playerAnswerLabel2
    
    # Ensure we start clean
    if 'playerAnswerContainer1' in globals() and playerAnswerContainer1 is not None:
        try:
            playerAnswerContainer1.destroy()
        except:
            pass
        playerAnswerContainer1 = None
        
    if 'playerAnswerContainer2' in globals() and playerAnswerContainer2 is not None:
        try:
            playerAnswerContainer2.destroy()
        except:
            pass
        playerAnswerContainer2 = None
    
    temp = answer.split('|')
    
    # Create first card
    playerAnswerContainer1 = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
    playerAnswerContainer1.place(relx=0.375, rely=0.15)
    playerAnswerLabel1 = Label(playerAnswerContainer1, text=temp[0], font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
    playerAnswerLabel1.place(relx=0.08, rely=0.05, anchor=NW)

    # Create second card
    playerAnswerContainer2 = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
    playerAnswerContainer2.place(relx=0.675, rely=0.15)
    playerAnswerLabel2 = Label(playerAnswerContainer2, text=temp[1], font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
    playerAnswerLabel2.place(relx=0.08, rely=0.05, anchor=NW)

    if readAloud == 'On' or readCardsOut == 'On':
        if '_____' in currentQuestion:
            read = currentQuestion.replace('_____', temp[0], 1)
            read = read.replace('_____', temp[1], 1)
            log(f"Reading (with blanks): {read}")
            readMessage(read)
        else:
            read = f"{currentQuestion} {temp[0]} {temp[1]}"
            log(f"Reading (question + answers): {read}")
            readMessage(read)

def display_one_card_answer(answer):
    """Helper function to display a one-card answer with proper cleanup first"""
    global playerAnswerContainer, playerAnswerLabel, currentQuestion
    
    # Ensure we start clean
    if 'playerAnswerContainer' in globals() and playerAnswerContainer is not None:
        try:
            playerAnswerContainer.destroy()
        except:
            pass
        playerAnswerContainer = None
    
    # Create single card
    playerAnswerContainer = createCurvedFrame(votingWindowCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="white")
    playerAnswerContainer.place(relx=0.55, rely=0.15)
    playerAnswerLabel = Label(playerAnswerContainer, text=answer, font=("Arial", int((35 * scaleWidth) * fontScale), 'bold'), bg="white", fg="black", wraplength=screenWidth * 0.25, justify=LEFT)
    playerAnswerLabel.place(relx=0.08, rely=0.05, anchor=NW)

    if readAloud == 'On' or readCardsOut == 'On':
        # Check if the question has a blank to fill in
        if '_____' in currentQuestion:
            # Replace the first blank with the answer
            read = currentQuestion.replace('_____', answer, 1)
            log(f"Reading (with blank): {read}")
            readMessage(read)
        else:
            # No blank - just read question followed by answer
            read = f"{currentQuestion} {answer}"
            log(f"Reading (question + answer): {read}")
            readMessage(read)

# This function begins the voting process by displaying the answers and starting the countdown
def beginVoting():
    global votingWindowCanvas, votingContainer, votingLabel, playerCountLabel, timeLeftLabel, countdownLabel, skipCountdownButtonImage, selectedUser
    
    # Final complete cleanup before voting starts
    complete_cleanup_voting_elements()

    # Reset voting container to standard voting position
    votingContainer.place(relx=0.1175, rely=0.15)
    
    # Force GUI update
    votingWindowCanvas.update()

    timeLeftLabel = votingWindowCanvas.create_text(screenWidth * 0.7175, screenHeight * 0.275, text="Time Left:", font=("Arial", int((30 * scaleWidth) * fontScale)), fill="white")
    countdownLabel = votingWindowCanvas.create_text(screenWidth * 0.7175, screenHeight * 0.55, text=str(votingCountdown), font=("Arial", int((500 * scaleWidth) * fontScale)), fill="white")
    
    if votingMethod == 'multi':
        playerCountLabel = votingWindowCanvas.create_text(screenWidth * 0.7175, screenHeight * 0.20, text="Players Answered: 0", font=("Arial", int((50 * scaleWidth) * fontScale)), fill="white")
        skipCountdownButtonImage = votingWindowCanvas.create_image(screenWidth * 0.7175, screenHeight * 0.87, image=skipLogo)
        votingWindowCanvas.tag_bind(skipCountdownButtonImage, "<Button-1>", lambda event: skipToResults())

    if readAloud == 'On':
        readMessage("Voting begins now")

    if votingMethod == 'single':
        changeGameState("voting-s", None)
    elif votingMethod == 'multi':
        changeGameState("voting-m")

    # Start countdown in a separate thread to prevent blocking
    threading.Thread(target=startCountdown, args=('votingWindowCanvas', votingCountdown), daemon=True).start()

# Also update the cleanup_voting_elements function (replace the old one):
def cleanup_voting_elements():
    """Legacy function - calls the complete cleanup"""
    complete_cleanup_voting_elements()

# This function receives the votes, counts them, determines the winner and then moves on accordingly
def updateVoteCount(winningAnswer, winningPlayer):
    global playersAnswered, playerCountLabel, votingWindowCanvas, countdown, votes
    playersAnswered += 1
    if votingMethod == 'multi':
        votingWindowCanvas.itemconfig(playerCountLabel, text=f"Players Answered: {playersAnswered}")
    if playersAnswered == len(users):
        countdown = 0
        votingWindowCanvas.itemconfig(countdownLabel, text="0")
    if votingMethod == 'single':
        countdown = 0
        playersAnswered = 0
        votingWindowCanvas.itemconfig(countdownLabel, text="0")
        updatePlayerScore(winningPlayer)
        buildWinnerWindow(winningAnswer, winningPlayer)
    if votingMethod == 'multi':
        votes.append(winningAnswer + "|" + winningPlayer)
        if playersAnswered == len(users):
            playersAnswered = 0
            winningAnswer = determineWinner(votes)
            temp = winningAnswer.split("|")
            length = len(temp)
            if length == 2:
                winningAnswer = temp[0]
                winningPlayer = temp[1]
            if length == 3:
                winningAnswer = temp[0] + "|" + temp[1]
                winningPlayer = temp[2]
            votes = []
            updatePlayerScore(winningPlayer)
            buildWinnerWindow(winningAnswer, winningPlayer)

# This function determines the winner of the round
def determineWinner(votes):
    countVotes = Counter(votes)
    collisionList = []
    key1, value1 = list(countVotes.items())[0]
    for i in range(len(countVotes)):
        y = i + 1
        if y >= len(countVotes):
            break
        tempKey, tempValue = list(countVotes.items())[y]
        if int(tempValue) > int(value1):
            key1 = tempKey
            value1 = tempValue
        if int(tempValue) == int(value1) and key1 != tempKey:
            collisionList.append(tempKey)
            if key1 not in collisionList:
                collisionList.append(key1)
            key1 = tempKey
            value1 = tempValue
    if len(collisionList) != 0:
        winner = collisionList[random.randint(0, len(collisionList)-1)]
    else:
        winner = key1
    
    return winner

# This function sends the winner to the backend server in order to update that users score
def updatePlayerScore(winningPlayer):
    data = f"command: updatePlayerScore, gameCode: {gameCode}, deviceID: {clientID}, agentType: host, winningPlayer: {winningPlayer}"
    threading.Thread(target=sendMessageToServer, args=(data,), daemon=True).start()

# This function requests the player scores from the backend server
def requestPlayerScores():
    try:
        data = f"command: getPlayerScores, gameCode: {gameCode}, deviceID: {clientID}, agentType: host"
        threading.Thread(target=sendMessageToServer, args=(data,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error requesting player scores", e)

# This function receieves the player scores from the backend server and then displays the top 3 on the scoreboard accordingly
def insertPlayerScores(scores):
    global firstContainerUsername, firstContainerScore, secondContainerUsername, secondContainerScore, thirdContainerUsername, thirdContainerScore, firstContainer, secondContainer, thirdContainer
    scores = eval(scores)
    scores = sorted(scores, key=lambda x: int(x.split('|')[-1]), reverse=True)

    if scores[1].split('|')[-1] == scores[0].split('|')[-1]:
        secondContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        secondContainer.pack(side=LEFT, anchor= S, padx = 40, pady=30)

        thirdContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.64, radius=25, bg_colour="#dfeef2")
        thirdContainer.pack(side=RIGHT, anchor= S, padx = 40, pady=30)

        firstContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        firstContainer.pack(side=BOTTOM, pady=30)

        secondContainerTitle = Label(secondContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        thirdContainerTitle = Label(thirdContainer, text="2nd", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        firstContainerTitle = Label(firstContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        secondContainerUsername = Label(secondContainer, text=scores[1].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        thirdContainerUsername = Label(thirdContainer, text=scores[2].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        firstContainerUsername = Label(firstContainer, text=scores[0].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        secondContainerScore = Label(secondContainer, text=f'Score: {scores[1].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        thirdContainerScore = Label(thirdContainer, text=f'Score: {scores[2].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        firstContainerScore = Label(firstContainer, text=f"Score: {scores[0].split('|')[1]}", font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)
    
    if scores[2].split('|')[-1] == scores[0].split('|')[-1]:
        secondContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        secondContainer.pack(side=LEFT, anchor= S, padx = 40, pady=30)

        thirdContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        thirdContainer.pack(side=RIGHT, anchor= S, padx = 40, pady=30)

        firstContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        firstContainer.pack(side=BOTTOM, pady=30)

        secondContainerTitle = Label(secondContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        thirdContainerTitle = Label(thirdContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        thirdContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        firstContainerTitle = Label(firstContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        secondContainerUsername = Label(secondContainer, text=scores[1].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        thirdContainerUsername = Label(thirdContainer, text=scores[2].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        thirdContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        firstContainerUsername = Label(firstContainer, text=scores[0].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        secondContainerScore = Label(secondContainer, text=f'Score: {scores[1].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        secondContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        thirdContainerScore = Label(thirdContainer, text=f'Score: {scores[2].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        thirdContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        firstContainerScore = Label(firstContainer, text=f"Score: {scores[0].split('|')[1]}", font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

    elif scores[2].split('|')[-1] == scores[1].split('|')[-1]:
        secondContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.64, radius=25, bg_colour="#dfeef2")
        secondContainer.pack(side=LEFT, anchor= S, padx = 40, pady=30)

        thirdContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.64, radius=25, bg_colour="#dfeef2")
        thirdContainer.pack(side=RIGHT, anchor= S, padx = 40, pady=30)

        firstContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        firstContainer.pack(side=BOTTOM, pady=30)

        secondContainerTitle = Label(secondContainer, text="2nd", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        thirdContainerTitle = Label(thirdContainer, text="2nd", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        firstContainerTitle = Label(firstContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        secondContainerUsername = Label(secondContainer, text=scores[1].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        thirdContainerUsername = Label(thirdContainer, text=scores[2].split('|')[0], font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        firstContainerUsername = Label(firstContainer, text=scores[0].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        secondContainerScore = Label(secondContainer, text=f'Score: {scores[1].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        thirdContainerScore = Label(thirdContainer, text=f'Score: {scores[2].split("|")[1]}', font=("Arial", int((25 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        thirdContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        firstContainerScore = Label(firstContainer, text=f"Score: {scores[0].split('|')[1]}", font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

    if scores[0].split('|')[-1] > scores[1].split('|')[-1] > scores[2].split('|')[-1]:
        secondContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.64, radius=25, bg_colour="#dfeef2")
        secondContainer.pack(side=LEFT, anchor=S, padx = 40, pady=30)

        thirdContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.48, radius=25, bg_colour="#bf902a")
        thirdContainer.pack(side=RIGHT, anchor=S, padx=40, pady=30)

        firstContainer = createCurvedFrame(scoreboardCanvas, screenWidth * 0.3, screenHeight * 0.8, radius=25, bg_colour="#f5c30f")
        firstContainer.pack(side=BOTTOM, pady=30)

        secondContainerTitle = Label(secondContainer, text="2nd", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        thirdContainerTitle = Label(thirdContainer, text="3rd", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#bf902a", fg="black")
        thirdContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        firstContainerTitle = Label(firstContainer, text="1st", font=("Arial", int((75 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerTitle.place(relx=0.5, rely=0.5, anchor=CENTER)

        secondContainerUsername = Label(secondContainer, text=scores[1].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        thirdContainerUsername = Label(thirdContainer, text=scores[2].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#bf902a", fg="black")
        thirdContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        firstContainerUsername = Label(firstContainer, text=scores[0].split('|')[0], font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerUsername.place(relx=0.5, rely=0.1, anchor=CENTER)

        secondContainerScore = Label(secondContainer, text=f'Score: {scores[1].split("|")[1]}', font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#dfeef2", fg="black")
        secondContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        thirdContainerScore = Label(thirdContainer, text=f'Score: {scores[2].split("|")[1]}', font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#bf902a", fg="black")
        thirdContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

        firstContainerScore = Label(firstContainer, text=f'Score: {scores[0].split("|")[1]}', font=("Arial", int((30 * scaleWidth) * fontScale), 'bold'), bg="#f5c30f", fg="black")
        firstContainerScore.place(relx=0.5, rely=0.9, anchor=CENTER)

# This function refreshes all values on the settings page with their current state
def refreshSettingsPage():
    getSettings()
    maxPlayersCurrentSettingLabel.config(text=str(maxPlayers))
    votingMethodCurrentSettingLabel.config(text=votingMethod)
    numberOfRoundsCurrentSettingLabel.config(text=str(numOfRounds))
    questionTimerCurrentSettingLabel.config(text=str(questionCountdown))
    votingTimerCurrentSettingLabel.config(text=str(votingCountdown))
    readCardsOutCurrentSettingLabel.config(text=readCardsOut)

    cardPackSizeCurrentSettingLabel.config(text=str(maxCardPackSize))

    fontSizeCurrentSettingLabel.config(text=str(int(fontScale * 100)) + "%")
    readAloudCurrentSettingLabel.config(text=readAloud)

# This function makes any requested changes to the settings database table
def settingsDBUpdate(setting, value):
    try:
        settingsDB = sqlite3.connect('Settings.db', check_same_thread=False)
        sDB = settingsDB.cursor()
        sDB.execute(f"UPDATE settings SET {setting} = '{value}'")
        settingsDB.commit()
    except Exception as e:
        messagebox.showerror("Error updating settings", e)

    refreshSettingsPage()

# This function changes the maximum number of players allowed in a game
def changeMaxPlayers(action):
    global maxPlayers
    gameSettingsErrorLabel.config(text="")
    if action == 'increase':
        if maxPlayers < 20:
            maxPlayers += 1
        else:
            gameSettingsErrorLabel.config(text="Max players cannot exceed 20", fg="red")
    if action == 'decrease':
        if maxPlayers > 3:
            maxPlayers -= 1
        else:
            gameSettingsErrorLabel.config(text="Minimum of 3 players required", fg="red")
    
    settingsDBUpdate("maxPlayers", maxPlayers)

# This function switches the default voting method between single and multi
def switchVotingMethod():
    global votingMethod
    gameSettingsErrorLabel.config(text="")
    if votingMethod == 'single':
        votingMethod = 'multi'
    else:
        votingMethod = 'single'
    
    settingsDBUpdate("votingMethod", votingMethod)

# This function changes the number of rounds in a game
def changeNumberOfRounds(action):
    global numOfRounds
    gameSettingsErrorLabel.config(text="")
    if action == 'increase':
        if numOfRounds == 'Unlimited':
            numOfRounds = '1'
        else:
            numOfRounds = str(int(numOfRounds) + 1)
    if action == 'decrease':
        if numOfRounds == '1':
            gameSettingsErrorLabel.config(text="Minimum of 1 round required", fg="red")
        else:
            numOfRounds = str(int(numOfRounds) - 1)
    if action == 'unlimited':
        numOfRounds = 0
    
    settingsDBUpdate("numOfRounds", numOfRounds)

# This function changes the question timer
def changeQuestionTimer(action):
    global questionCountdown
    gameSettingsErrorLabel.config(text="")
    if action == 'increase':
        questionCountdown += 5
    if action == 'decrease':
        if questionCountdown > 5:
            questionCountdown -= 5
        else:
            gameSettingsErrorLabel.config(text="Question timer cannot be less than 5 seconds", fg="red")
    
    settingsDBUpdate("questionCountdown", questionCountdown)

# This function changes the voting timer
def changeVotingTimer(action):
    global votingCountdown
    gameSettingsErrorLabel.config(text="")
    if action == 'increase':
        votingCountdown += 5
    if action == 'decrease':
        if votingCountdown > 5:
            votingCountdown -= 5
        else:
            gameSettingsErrorLabel.config(text="Voting timer cannot be less than 5 seconds", fg="red")
    
    settingsDBUpdate("votingCountdown", votingCountdown)

# This function changes the maximum number of cards in a card pack
def changeCardPackSize(action):
    global maxCardPackSize
    cardPackSettingsErrorLabel.config(text="")
    if action == 'increase':
        if maxCardPackSize == 'Unlimited':
            maxCardPackSize = str(int(0))
        maxCardPackSize = str(int(maxCardPackSize) + 5)
    if action == 'decrease':
        if maxCardPackSize == 'Unlimited':
            maxCardPackSize = str(int(10))
        if int(maxCardPackSize) > 5:
            if maxCardPackSize == 'Unlimited':
                maxCardPackSize = str(int(5))
            maxCardPackSize = str(int(maxCardPackSize) - 5)
        else:
            cardPackSettingsErrorLabel.config(text="Card pack size cannot be less than 5", fg="red")
    if action == 'unlimited':
        maxCardPackSize = str(int(0))
    
    settingsDBUpdate("maxCardPackSize", int(maxCardPackSize))

# This function changes the font size of the game
def changeFontScale(action):
    global fontScale
    accessibilitySettingsErrorLabel.config(text="")

    if action == 'increase':
        if round(fontScale, 2) < 1.1:
            fontScale = round(fontScale + 0.01, 2)
        else:
            accessibilitySettingsErrorLabel.config(text="Font size cannot exceed 110%", fg="red")
            return
    
    elif action == 'decrease':
        if round(fontScale, 2) > 0.5:
            fontScale = round(fontScale - 0.01, 2)
        else:
            accessibilitySettingsErrorLabel.config(text="Font size cannot be less than 50%", fg="red")
            return

    settingsDBUpdate("fontScale", int(fontScale * 100))
    settingsWindowCanvas.destroy()
    buildSettingsWindow()

# This function switches the read cards out setting
def switchReadCardsOut():
    global readCardsOut
    accessibilitySettingsErrorLabel.config(text="")
    if readCardsOut == 'On':
        readCardsOut = 0
    else:
        readCardsOut = 1
    
    settingsDBUpdate("readCardsOut", readCardsOut)

# This function switches the read aloud setting
def switchReadAloud():
    global readAloud
    accessibilitySettingsErrorLabel.config(text="")
    if readAloud == 'On':
        readAloud = 0
        stopPlayback()
    else:
        readAloud = 1
    
    settingsDBUpdate("readAloud", readAloud)

# This function reverts all game settings to their default values
def revertGameSettingsToDefault():
    settingsDBUpdate("maxPlayers", 20)
    settingsDBUpdate("votingMethod", 'multi')
    settingsDBUpdate("numOfRounds", 0)
    settingsDBUpdate("questionCountdown", 60)
    settingsDBUpdate("votingCountdown", 60)
    settingsDBUpdate("readCardsOut", 0)

# This function reverts all card pack settings to their default values
def revertCardPackSettingsToDefault():
    settingsDBUpdate("maxCardPackSize", 0)

# This function reverts all accessibility settings to their default values
def revertAccessibilitySettingsToDefault():
    settingsDBUpdate("fontScale", 100)
    settingsDBUpdate("readAloud", 0)
    settingsWindowCanvas.destroy()
    buildSettingsWindow()

# This function checks the connection to the backend server
def checkConnection():
    try:
        response = requests.get(f"{base_url}/checkConnection")
        if response.status_code == 200:
            changeCurvedButtonColour(checkConnectionButton, checkConnectionButton.label_id, "green")
            unbindCurvedButton(checkConnectionButton, checkConnectionButton.label_id)
            rebindCurvedButton(checkConnectionButton, checkConnectionButton.label_id, "green", "#7a7a7a")
        else:
            changeCurvedButtonColour(checkConnectionButton, checkConnectionButton.label_id, "red")
            unbindCurvedButton(checkConnectionButton, checkConnectionButton.label_id)
            rebindCurvedButton(checkConnectionButton, checkConnectionButton.label_id, "red", "#7a7a7a")
    except Exception as e:
        changeCurvedButtonColour(checkConnectionButton, checkConnectionButton.label_id, "red")
        unbindCurvedButton(checkConnectionButton, checkConnectionButton.label_id)
        rebindCurvedButton(checkConnectionButton, checkConnectionButton.label_id, "red", "#7a7a7a")

# This function exits the game mode and takes the host back to the welcome screen
def exitGame():
    global continueGame
    continueGame = False

    # Stop background music when exiting game
    try:
        streamAudio(state="stop")
        log("🎵 Stopped background music on game exit")
    except Exception as e:
        log(f"Error stopping audio on exit: {e}")

    if readAloud == 'On':
        readMessage("Exiting game")

    try:
        data = f"command: endGame, gameCode: {gameCode}, deviceID: {clientID}, agentType: host"
        threading.Thread(target=sendMessageToServer, args=(data,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error exiting game", e)
    buildWelcomeWindow()

# This function starts the GUI up upon application startup
def startGUI():
    try:
        global welcomeWindow
        setScreenDimensions()
        welcomeWindow = Tk()
        welcomeWindow.title("Welcome")
        welcomeWindow.geometry("500x200")
        setMonitor(defaultMonitor, welcomeWindow)
        welcomeWindow.resizable(False, False)
        welcomeWindow.configure(bg="black")
        welcomeWindow.attributes("-fullscreen", True)
        welcomeWindow.iconbitmap(resource_path("Images/DAH.ico"))
        
        # Add periodic check for shutdown flag
        def check_shutdown():
            global shutdown_flag
            if shutdown_flag:
                welcomeWindow.quit()
                welcomeWindow.destroy()
                os._exit(0)
            welcomeWindow.after(100, check_shutdown)  # Check every 100ms
        
        buildWelcomeWindow()
        check_shutdown()  # Start the check
        welcomeWindow.mainloop()
    except Exception as e:
        messagebox.showerror("Error starting GUI", e)
        exit()

def streamAudio(state="start", url="https://youtu.be/triXo_xCqms?si=xJUWQm4AM3MSGfHR"):
    global _audio_player, _audio_media, _audio_state, _audio_position_ms, _audio_lock, _audio_stream_url
    
    with _audio_lock:
        if state == "start":
            # Can only start if currently stopped or paused
            if _audio_state == "playing":
                log("⚠️ Audio already playing. Use 'pause' or 'stop' first.")
                return
            
            # Stop any existing playback
            if _audio_player is not None:
                _audio_player.stop()
            
            # Extract best audio stream URL using yt_dlp
            try:
                ydl_opts = {'format': 'bestaudio', 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    _audio_stream_url = info['url']
                
                # Create new VLC player and media
                _audio_player = vlc.MediaPlayer(_audio_stream_url)
                _audio_media = _audio_player.get_media()
                _audio_position_ms = 0
                
                # Start playback from beginning
                _audio_player.play()
                _audio_state = "playing"
                log("🎧 Streaming audio from beginning...")

                try:
                    toggleMusicButton(option = "on")
                except:
                    pass
                
            except Exception as e:
                log(f"❌ Error starting audio: {e}")
                _audio_state = "stopped"
                return
        
        elif state == "play":
            # Resume from saved position
            if _audio_state == "playing":
                log("⚠️ Audio already playing.")
                return
            
            if _audio_player is None:
                log("⚠️ No audio initialized. Use 'start' first.")
                return
            
            # Resume playback
            if _audio_state == "paused":
                _audio_player.play()
                # Restore saved position
                if _audio_position_ms > 0:
                    _audio_player.set_time(_audio_position_ms)
                _audio_state = "playing"
                log(f"▶️ Resuming audio from {_audio_position_ms}ms...")
            elif _audio_state == "stopped":
                # If stopped, need to recreate player
                if _audio_stream_url is None:
                    log("⚠️ No audio URL available. Use 'start' first.")
                    return
                _audio_player = vlc.MediaPlayer(_audio_stream_url)
                _audio_player.play()
                if _audio_position_ms > 0:
                    _audio_player.set_time(_audio_position_ms)
                _audio_state = "playing"
                log(f"▶️ Playing audio from {_audio_position_ms}ms...")
        
        elif state == "pause":
            # Pause and save position
            if _audio_state != "playing":
                log("⚠️ Audio not currently playing.")
                return
            
            if _audio_player is not None:
                # Save current position before pausing
                _audio_position_ms = _audio_player.get_time()
                _audio_player.pause()
                _audio_state = "paused"
                log(f"⏸️ Paused audio at {_audio_position_ms}ms")
        
        elif state == "stop":
            # Stop completely and reset
            if _audio_player is not None:
                _audio_player.stop()
                _audio_position_ms = 0
                _audio_state = "stopped"
                log("⏹️ Stopped audio (position reset)")
            else:
                log("⚠️ No audio player active.")
        
        else:
            log(f"❌ Invalid state: '{state}'. Use 'start', 'play', 'pause', or 'stop'.")

# This allows initial variables and settings to be set before the GUI is started
if __name__ == "__main__":
    # check if the settings database exists, if not create it
    if not os.path.exists('Settings.db'):
        settingsDB = sqlite3.connect('Settings.db', check_same_thread=False)
        sDB = settingsDB.cursor()
        sDB.execute("CREATE TABLE settings (maxPlayers INTEGER, votingMethod TEXT, numOfRounds INTEGER, questionCountdown INTEGER, votingCountdown INTEGER, readCardsOut INTEGER, maxCardPackSize INTEGER, fontScale INTEGER, readAloud INTEGER)")
        sDB.execute("INSERT INTO settings (maxPlayers, votingMethod, numOfRounds, questionCountdown, votingCountdown, readCardsOut, maxCardPackSize, fontScale, readAloud) VALUES (20, 'multi', 0, 60, 60, 0, 0, 100, 0)")
        settingsDB.commit()
    base_url = "https://{serverURL}"
    getSettings()
    generateUniqueID()
    global conn, c
    conn = sqlite3.connect('CardPacks.db', check_same_thread=False)
    c = conn.cursor()
    startGUI()