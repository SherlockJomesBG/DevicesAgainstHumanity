# 🧠 Devices Against Humanity  
*An online multiplayer parody party game — play together from your phones!*

> **Disclaimer:** *Devices Against Humanity* is an independent, non-commercial parody project and is **not affiliated with or endorsed by Cards Against Humanity LLC**.  
> All rights to the *Cards Against Humanity* name and game belong to their respective owners.

---

## 🕹️ Overview

**Devices Against Humanity** is a digital, online-based parody of *Cards Against Humanity*, designed for play with friends together or far apart.  
The host runs the desktop app, and players join through a website on their phones, tablets, or laptops!

This project includes:

- `host.py` — The desktop application for hosting and managing games  
- `server.py` — The backend game server that handles game state, connections, and WebSocket messaging (not seen or ran by the users)
- `website/` — The web client for players to connect, submit answers, and vote  

---

## ✨ Features

### 💻 Host Application (`host.py`)

- Built with **Tkinter** for a full-featured GUI  
- **Create and manage games** with real-time player updates  
- **Join code system** for easy player connections  
- **QR code generation** linking players to the website  
- **Custom card pack editor** to create, modify, and delete cards  
- **Accessibility options** such as text-to-speech and font scaling  
- **Real-time WebSocket communication** with the backend server  
- **Animated loading & feedback UI** for smooth gameplay  
- **Built-in scoreboard** showing top 3 players
- **Game settings panel** to configure rounds, time limits, and voting modes  

### 🧠 Server (`server.py`)

- Manages **game state**, **player sessions**, and **WebSocket events**  
- Assigns **unique 6-digit game codes** and **8-digit device IDs**  
- Handles all database queries
- Processes card pack uploads from hosts  
- Relays messages between host and clients in real time  
- Built with **FastAPI** and **WebSockets** for high responsiveness  

### 🌐 Website

- Accessible via `https://devicesagainsthumanity.bgodfrey.org`
- Players can:
  - Join using the host’s code
  - Submit white card responses to prompts  
  - Vote on the funniest answer  
  - View round results and standings live  
- Responsive and mobile-optimised interface  
- Built for low-latency communication via WebSockets  

---

## 🧩 Known Issues

This is an early public release — expect a few bugs along the way:

| Type | Description |
|------|--------------|
| 📊 UI | The scoreboard may still occasionally fail to display after some rounds. |
| 🚫 Game Flow | Players joining mid-game can still cause instability or crashes. |
| 📱 Mobile | Some mobile browsers may require a refresh to reconnect after idle timeouts. |
| 🎵 Game Music | On Windows, if the game is exited abruptly mid round (not via the end game buttons) then the audio continues to play. Only way to stop at current is via task manager. macOS does not suffer this issue |

---

## 🔧 Planned Improvements

- Automatic WebSocket reconnection  
- Mid-game joining support  
- Persistent score tracking between sessions  
- Improved scoreboard synchronization  

---

## 🚀 How to Run

### 🎮 Host

1. Download the release package from the [Releases](../../releases) page.  
2. Install `Devices Against Humanity Setup.exe` (Windows)
3. The app will display a **join QR code** and **game code**.  

(I am working on packaging the host for macOS and Linux)

### 🌍 Players

1. Visit the website (e.g., `https://devicesagainsthumanity.bgodfrey.org`).  
2. Enter the **game code** from the host’s screen.  
3. Wait for the host to start the game — then play!  

---

## 🧠 Technical Details

- **Language:** Python 3.10+  
- **Libraries:** Tkinter, asyncio, websockets, requests, qrcode, Pillow  
- **Backend:** FastAPI (ASGI) with WebSocket support  
- **Frontend:** HTML + JavaScript, connected over WebSocket  
- **Data Handling:** In-memory or lightweight SQLite for active sessions  

---

## ⚖️ Legal Disclaimer

> **Devices Against Humanity** is a personal, educational, and non-commercial parody project.  
> It is **not affiliated with, endorsed by, or connected to Cards Against Humanity LLC**.  
> All names, references, and trademarks belong to their respective owners.  
> This project is distributed freely and is not intended for resale or monetization.

---
