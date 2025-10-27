# Import Required Libraries and Modules
# FastAPI used for creating the server and managing the websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
#Random used for generating the Random IDs and Game Codes
import random
#SQLite3 used for managing the databases
import sqlite3
#Typing used for defining the types of the variables
from typing import Dict
#Datetime used for logging the time of the messages
import datetime
import time
#JSON used for formatting data sent and received
import json
import psutil
from flask import jsonify

# Creating and initializing the server
server = FastAPI()

# Setting the dictionaries to store the websocket connections
active_connections: Dict[WebSocket, str] = {}
activeHostConnections: Dict[WebSocket, str] = {}
activeClientConnections: Dict[WebSocket, str] = {}

# Adding the CORS Middleware to allow the server to be accessed from different origins
origins = [
    "ORIGIN_PLACEHOLDER"
]

server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

global conn, c
conn = sqlite3.connect('../Databases/DevicesAgainstHumanity.db')
c = conn.cursor()

# This function logs messages to a log file for debugging purposes and keeps the terminal clean
def log(message):
    # This gets the current date and time
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    # This opens the log file, writes the message to it and closes again
    file = open(f"../Logs/{date}.log", "a")
    file.write(f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
    file.close()

# This defines the route for all devices to generate a UniqueID
@server.get("/uniqueID")
async def getUniqueID():
    global conn, c
    uniqueId = ""
    # By setting this to true it ensures that the while loop runs at least once to check if the ID already exists
    idExists = True
    while idExists:
        # Generates a random 6 digit number using the random library
        uniqueId = "".join([str(random.randint(1, 9)) for _ in range(6)])

        # Connects to the database and checks if the ID already exists
        c.execute("SELECT * FROM users WHERE websocketID = ?", (uniqueId,))
        idExists = c.fetchone() is not None
    # Returns the unique ID when it is satisfied that it is unique
    return {uniqueId}

# This defines the route for all hosts to gain a game code
@server.get("/getCode")
async def getCode():
    global conn, c
    game_code = ""
    # By setting this to true it ensures that the while loop runs at least once to check if the game code already exists
    code_exists = True
    while code_exists:
        # Generates a random 6 digit number using the random library
        game_code = "".join([str(random.randint(1, 9)) for _ in range(6)])

        # Connects to the database and checks if the game code already exists
        c.execute("SELECT * FROM games WHERE roomCode = ?", (game_code,))
        code_exists = c.fetchone() is not None

    # Connects to the database and creates a new record for the game
    c.execute("INSERT INTO games (roomCode, playersCount, gameState) VALUES (?, ?, ?)", (game_code, 0, 'waiting'))
    conn.commit()

    # Connects to the database and creates a new database for the game which is used to track the cards used in the game
    c.execute(f'''CREATE TABLE IF NOT EXISTS "{game_code}blackCards" (
        id INTEGER PRIMARY KEY,
        question TEXT,
        answerNum INTEGER
    )''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS "{game_code}whiteCards" (
        id INTEGER PRIMARY KEY,
        answer TEXT,
        username TEXT
    )''')
    conn.commit()

    # Returns the game code when it is satisfied that it is unique
    return {"game_code": game_code}

# This function sets up the websocket connection for both clients and hosts
async def setupWebsocket(websocket, clientID, data):
    # Define global variables
    global activeHostConnections
    global activeClientConnections
    global active_connections
    global conn, c

    # Logs message to the log file
    log("Setting up websocket")

    # Extracts the agent type from the data received and then sets the websocket up accordingly
    agentType = data[3].split(": ")[1].strip('"')
    log(f"Data: {data}")
    log(f"Agent Type: {agentType}")
    if agentType == "host":
        # If host then it is added to the active host connections dictionary
        activeHostConnections[websocket] = clientID

        # Connects to the games database and updates the websocketID for the game
        c.execute("UPDATE games SET websocketID = ? WHERE roomCode = ?", (data[2].split(": ")[1].strip('"'), data[1].split(": ")[1].strip('"')))
        conn.commit()

    elif agentType == "client":
        # If client then it is added to the active client connections dictionary
        activeClientConnections[websocket] = clientID

        # Connects to the users database and updates the websocketID for the user
        c.execute("UPDATE users SET websocketID = ? WHERE username = ? AND roomCode = ?", (data[2].split(": ")[1].strip('"'), data[4].split(": ")[1].strip('"'), data[1].split(": ")[1].strip('"')))
        conn.commit()

        # Sends a message to the host to add the user to the game
        await sendMessageToHost(data[1].split(": ")[1].strip('"'), "addUser:" + data[4].split(": ")[1].strip('"'))
    
    # Logs the current connections in each dictionary
    log(f"Active connections: {active_connections}")
    log(f"Active host connections: {activeHostConnections}")
    log(f"Active client connections: {activeClientConnections}")

# This defines the route for devices to connect and open a websocket connection to the server
@server.websocket("/ws/{clientID}")
async def websocketEndpoint(websocket: WebSocket, clientID: str):
    global conn, c
    # Waits for the websocket to be accepted
    await websocket.accept()

    # Adds the websocket to the active connections dictionary
    active_connections[websocket] = clientID

    try:
        # This then picks apart the data received and runs the appropriate function
        while True:
            # Waits for a message to be received
            data = await websocket.receive_text()

            # This removes any curly brackets from the data for formatting purposes
            if '{' in data:
                data = data[:-1]
                data = data[:0]
            
            # This logs what is received and from who
            log(f"Received message from {clientID}: {data}")

            # This splits the data into a list for better handling
            data = data.split(", ")
            log(f"Data: {data}")

            # This then checks the first part of the data to determine what function to run
            if data[0].split(": ")[1].strip('"') == "setupWebsocket":
                await setupWebsocket(websocket, clientID, data)
            if data[0].split(": ")[1].strip('"') == "getBlackCard":
                await getBlackCard(gameCode = data[1].split(": ")[1].strip('"'))
            if "getWhiteCards" in data[0].split(": ")[1].strip('"'):
                await getWhiteCards(data)
            if data[0].split(": ")[1].strip('"') == "changeGameState":
                await changeGameState(data)
            if data[0].split(": ")[1].strip('"') == "submitCards":
                await submitCards(data)
            if data[0].split(": ")[1].strip('"') == "submitVote":
                await submitVote(data)
            if data[0].split(": ")[1].strip('"') == "getAnswers":
                await getAnswers(data)
            if data[0].split(": ")[1].strip('"') == "transferCardPacks":
                await transferCardPacks(data)
            if data[0].split(": ")[1].strip('"') == "uploadCard":
                await insertCustomCard(data)
            if data[0].split(": ")[1].strip('"') == "selectVoter":
                await selectVoter(data)
            if data[0].split(": ")[1].strip('"') == "updatePlayerScore":
                await updatePlayerScore(data)
            if data[0].split(": ")[1].strip('"') == "getPlayerScores":
                await getPlayerScores(data)
            if data[0].split(": ")[1].strip('"') == "endGame":
                await endGame(data)
            if data[0].split(": ")[1].strip('"') == "ping":
                await websocket.send_text("pong")
                log(f"Ping received from {clientID}, pong sent")

    except WebSocketDisconnect:
        # If the websocket disconnects then it is removed from the active connections dictionary to prevent errors and to keep the server clean
        # At a later stage we would add in support for saving the websocket in case the device reconnects

        # This deletes the websocket from the active connections dictionary
        del active_connections[websocket]
        log(f"Client {clientID} disconnected")

        try:
            del activeHostConnections[websocket]
        except:
            pass
        try:
            del activeClientConnections[websocket]
        except:
            pass

        # This then attempts to remove the user from the game if they are a client
        try:
            log(f"Client ID: {clientID}")

            # This extracts the username and game code from the users database
            c.execute("SELECT username, roomCode FROM users WHERE websocketID = ?", (clientID,))
            data = c.fetchone()

            log(f"Data: {data}")

            username = data[0]
            gameCode = data[1]

            # This then removes the user from the game
            c.execute("DELETE FROM users WHERE username = ? AND roomCode = ?", (username, gameCode))
            conn.commit()

            # This then updates the player count in the games database
            c.execute("UPDATE games SET playersCount = playersCount - 1 WHERE roomCode = ?", (gameCode,))
            conn.commit()

            # This then sends a message to the host to remove the user from the game
            await sendMessageToHost(gameCode, f"removeUser:{username}")
        except Exception as e:
            # If there is an error then it logs the error
            log(f"Error removing user from game: {e}")

# This defines the route for clients to join a game
@server.post("/joinGame")
async def joinGame(request: Request):
    # Waits for the request to be received
    data = await request.json()

    # Extracts the game code and username from the data
    gameCode = data.get("gameCode")
    username = data.get("username")

    # Checks that the game exists
    c.execute("SELECT * FROM games WHERE roomCode = ?", (gameCode,))
    game = c.fetchone()
    if game is None:
        return {"status": "game not found"}
    
    # Checks that the user does not already exist in the game
    c.execute("SELECT * FROM users WHERE username =? AND roomCode = ?", (username, gameCode))
    user = c.fetchone()
    if user is not None:
        return {"status": "user already exists"}
    
    # Adds the user to the users database and ties them to the game
    c.execute("INSERT INTO users (username, roomCode, score) VALUES (?, ?, ?)", (username, gameCode, 0))
    conn.commit()
    
    # Updates the player count in the games database
    c.execute("UPDATE games SET playersCount = playersCount + 1 WHERE roomCode = ?", (gameCode,))
    conn.commit()

    # Logs the user joining the game
    log(f"User {username} joined game {gameCode}")
    return {"status": "user added to game"}

@server.get("/getCardPacks")
async def getCardPacks():
    return {"cardPacks": ["0StandardBlack", "1StandardWhite"]}

@server.get("/checkConnection")
async def checkConnection():
    return {"status": "connected"}

# This function extracts a black card for the host when requested
async def getBlackCard(gameCode):
    log(f"Getting black card for game {gameCode}")

    # Grabs a random black card from the black cards database
    c.execute(f"SELECT * FROM '{gameCode}blackCards' ORDER BY RANDOM() LIMIT 1")
    question = c.fetchone()
    question = question[1]
    log(f"Question: {question}")
    try:
        await sendMessageToHost(gameCode, f"blackCard:{question}")
    except Exception as e:
        # If there is an error then it logs the error
        log(f"Error sending black card to host: {e}")

    c.execute(f"DELETE FROM '{gameCode}blackCards' WHERE question = ?", (question,))
    conn.commit()

# This function extracts white cards for the clients when requested
async def getWhiteCards(data):
    # Extracts the number of cards required, the game code, the device ID and the username from the data
    numOfCards = data[0].split(": ")[1].strip('"')
    numOfCards = numOfCards.split("|")
    numCardsRequired = int(numOfCards[1])
    log(f'numCardsRequired: {numCardsRequired}')
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    username = data[4].split(": ")[1].strip('"')
    log(f"Getting {numCardsRequired} white cards for game {gameCode}")
    
    whiteCards = []

    while len(whiteCards) < numCardsRequired:
        # Calculates the number of cards needed
        remainingCardsNeeded = numCardsRequired - len(whiteCards)
        # Grabs the required number of cards from the standard cards database randomly
        c.execute(f"SELECT * FROM '{gameCode}whiteCards' ORDER BY RANDOM() LIMIT ?", (remainingCardsNeeded,))
        randomCards = c.fetchall()
        for card in randomCards:
            whiteCards.append(card)

    # Sends the white cards to the client
    whiteCardsList = [card[1] for card in whiteCards]
    log(f"White cards: {whiteCardsList}")
    await sendMessageToClient(deviceID, f"whiteCards:{json.dumps(whiteCardsList)}")
    for card in whiteCardsList:
        c.execute(f"DELETE FROM '{gameCode}whiteCards' WHERE answer = ?", (card,))
        conn.commit()

async def selectVoter(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    username = data[4].split(": ")[1].strip('"')

    c.execute("SELECT websocketID FROM users WHERE roomCode = ? AND username = ?", (gameCode, username))
    voter = c.fetchone()[0]

    await sendMessageToClient(voter, f"changeGameState:voter")

# This function changes the game state of a game and then sends the new game state to the clients
async def changeGameState(data):
    # Extracts the game code and the new game state from the data
    gameCode = data[1].split(": ")[1].strip('"')
    gameState = data[4].split(": ")[1].strip('"')
    if gameState == 'playing':
        answersRequired = int(data[5].split(": ")[1].strip('"'))
        c.execute("UPDATE users SET answer = NULL WHERE roomCode = ?", (gameCode,))
        conn.commit()

    # Updates the game state in the games database
    c.execute("UPDATE games SET gameState = ? WHERE roomCode = ?", (gameState, gameCode))
    conn.commit()

    await sendMessageToClients(gameCode, f"changeGameState:{gameState}")

    if gameState == 'playing':
        await sendMessageToClients(gameCode, f"answersRequired:{answersRequired}")

async def insertCustomCard(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    cardType = data[4].split(": ")[1].strip('"')
    cardText = data[6].split(": ")[1].strip('"')
    if cardType == 'black':
        answerNum = data[7].split(": ")[1].strip('"')

    if cardType == 'black':
        c.execute(f'INSERT INTO "{gameCode}blackCards" (question, answerNum) VALUES (?, ?)', (cardText, answerNum))
        conn.commit()
    elif cardType == 'white':
        c.execute(f'INSERT INTO "{gameCode}whiteCards" (answer) VALUES (?)', (cardText,))
        conn.commit()
    
async def submitCards(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    username = data[4].split(": ")[1].strip('"')
    cards = data[5].split(": ")[1].strip('"')
    
    c.execute("SELECT * FROM users WHERE websocketID = ?", (deviceID,))
    user = c.fetchone()

    if user is not None:
        c.execute("UPDATE users SET answer = ? WHERE websocketID = ? AND roomCode = ?", (cards, deviceID, gameCode))
        conn.commit()

    await sendMessageToHost(gameCode, f"updateAnswerCount")

async def submitVote(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    vote = data[5].split(": ")[1].strip('"')

    c.execute("SELECT username FROM users WHERE roomCode = ? AND answer = ?", (gameCode, vote))
    user = c.fetchone()

    user = user[0]

    await sendMessageToHost(gameCode, f"updateVoteCount/{vote}/{user}")

async def transferCardPacks(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')
    cardPacks = data[4].split(": ")[1].strip('"')
    cardPacks = cardPacks.split(",")

    savedCardPacks = ['0StandardBlack', '1StandardWhite']

    def process_black_cards(gameCode, blackCards, conn):
        c = conn.cursor()
        # Use an f-string for the table name only
        for blackCard in blackCards:
            c.execute(f"INSERT INTO '{gameCode}blackCards' (question, answerNum) VALUES (?, ?)", (blackCard[0], blackCard[1]))
        conn.commit()


    def process_white_cards(gameCode, whiteCards, conn):
        c = conn.cursor()
        # Use an f-string for the table name only
        for whiteCard in whiteCards:
            c.execute(f"INSERT INTO '{gameCode}whiteCards' (answer) VALUES (?)", (whiteCard[0],))
        conn.commit()


    # Main processing logic
    to_remove = []
    with sqlite3.connect('../Databases/DevicesAgainstHumanity.db') as conn:
        for cardPack in cardPacks:
            if cardPack in savedCardPacks:
                cardPackType = cardPack[0]
                
                # Fetch and process black cards
                if cardPackType == "0":
                    c = conn.cursor()
                    c.execute("SELECT * FROM '0StandardBlack'")
                    blackCards = c.fetchall()
                    process_black_cards(gameCode, blackCards, conn)
                    to_remove.append(cardPack)

                # Fetch and process white cards
                elif cardPackType == "1":
                    c = conn.cursor()
                    c.execute("SELECT * FROM '1StandardWhite'")
                    whiteCards = c.fetchall()
                    process_white_cards(gameCode, whiteCards, conn)
                    to_remove.append(cardPack)

    # Remove processed packs after iteration
    for cardPack in to_remove:
        cardPacks.remove(cardPack)

    if len(cardPacks) != 0:
        global awaitingCardPacks
        awaitingCardPacks = len(cardPacks)
        for cardPack in cardPacks:
            await sendMessageToHost(gameCode, f"cardPackRequest:{cardPack}")
    await sendMessageToHost(gameCode, f"cardPacksTransferred")

async def getAnswers(data):
    gameCode = data[1].split(": ")[1].strip('"')
    deviceID = data[2].split(": ")[1].strip('"')

    c.execute("SELECT answer FROM users WHERE roomCode = ? AND answer IS NOT NULL", (gameCode,))
    answers = c.fetchall()

    answers = [answer[0] for answer in answers]

    log(f"Answers: {answers}")

    await sendMessageToHost(gameCode, f"answers:{json.dumps(answers)}")
    await sendMessageToClients(gameCode, f"answers:{json.dumps(answers)}")

async def updatePlayerScore(data):
    gameCode = data[1].split(": ")[1].strip('"')
    winningPlayer = data[4].split(": ")[1].strip('"')

    c.execute("SELECT score FROM users WHERE roomCode = ? AND username = ?", (gameCode, winningPlayer))
    score = c.fetchone()
    score = score[0]
    score = int(score) + 1

    c.execute("UPDATE users SET score = ? WHERE roomCode = ? AND username = ?", (score, gameCode, winningPlayer))
    conn.commit()

    c.execute("SELECT websocketID FROM users WHERE roomCode = ? AND username = ?", (gameCode, winningPlayer))
    websocketID = c.fetchone()
    websocketID = websocketID[0]

    await sendMessageToClient(websocketID, 'updateScore')

async def getPlayerScores(data):
    gameCode = data[1].split(": ")[1].strip('"')

    temp = []

    c.execute("SELECT username, score FROM users WHERE roomCode = ?", (gameCode,))
    scores = c.fetchall()

    for user in scores:
        temp.append(f"{user[0]}|{user[1]}")

    await sendMessageToHost(gameCode, f"playerScores:{json.dumps(temp)}")

async def endGame(data):
    gameCode = data[1].split(": ")[1].strip('"')

    c.execute("SELECT websocketID FROM users WHERE roomCode = ?", (gameCode,))
    webSocketIDs = c.fetchall()
    webSocketIDs = [ws[0] for ws in webSocketIDs]

    for ws in webSocketIDs:
        await sendMessageToClient(ws, 'endGame')
        for key, value in activeClientConnections.items():
            if str(value) == str(ws):
                del activeClientConnections[key]
                break
            else:
                pass

    c.execute("SELECT websocketID FROM games WHERE roomCode = ?", (gameCode,))
    webSocketID = c.fetchone()[0]
    
    for key, value in activeHostConnections.items():
        if str(value) == str(webSocketID):
            del activeHostConnections[key]
            break
        else:
            pass

    c.execute("DELETE FROM games WHERE roomCode = ?", (gameCode,))
    conn.commit()

    c.execute(f"DROP TABLE '{gameCode}blackCards'")
    conn.commit()

    c.execute(f"DROP TABLE '{gameCode}whiteCards'")
    conn.commit()

    await sendMessageToClients(gameCode, 'endGame')

    c.execute("DELETE FROM users WHERE roomCode = ?", (gameCode,))
    conn.commit()

    log(f"Game {gameCode} ended")

# This function sends messages to the host devices
async def sendMessageToHost(gameCode, message):
    log(f'Sending message to host {gameCode}: {message}')

    # Connects to the games database and grabs the websocketID for the game host
    c.execute("SELECT websocketID FROM games WHERE roomCode = ?", (gameCode,))
    webSocketID = c.fetchone()[0]
    log(f"Websocket ID: {webSocketID}")

    # Compares the websocketID to the active host connections to find the correct websocket and then sends the message
    for key, value in activeHostConnections.items():
        log(f"Key: {key}, Value: {value}")
        log("Searching")
        if str(value) == str(webSocketID):
            wsID = key
            log(f"Sending message to host {gameCode}:{wsID}")
            await wsID.send_text(message)
            break
        else:
            pass

# This function sends messages to multiple client devices
async def sendMessageToClients(gameCode, message):
    log(f'Sending message to clients {gameCode}: {message}')
    relevantClients = []

    # Connects to the users database and grabs the websocketID for all the clients in the game
    c.execute("SELECT websocketID FROM users WHERE roomCode = ?", (gameCode,))
    webSocketIDs = c.fetchall()

    # Compares the websocketID to the active client connections to find the correct websockets
    for i in range(len(webSocketIDs)):
        for key, value in activeClientConnections.items():
            if str(value) == str(webSocketIDs[i][0]):
                log(f"Sending message to client {gameCode}:{key}")
                relevantClients.append(key)
            else:
                pass

    log(f'Relevant clients: {relevantClients}')

    # Sends the message to all the relevant clients
    for client in relevantClients:
        await client.send_text(message)

# This function sends messages to a single client device
async def sendMessageToClient(deviceID, message):
    log(f'Sending message to client {deviceID}: {message}')

    # Compares the websocketID to the active client connections to find the correct websocket and then sends the message
    for key, value in activeClientConnections.items():
        if str(value) == str(deviceID):
            wsID = key
            log(f"Sending message to client {deviceID}:{wsID}")
            await wsID.send_text(message)
            break
        else:
            pass

# Script is started here
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(server, host="0.0.0.0", port=9090)
