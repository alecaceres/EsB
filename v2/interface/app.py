from flask import Flask, request, session, redirect, url_for, jsonify, render_template
import queue
import threading
import os
import pygame
import serial
import serial.tools.list_ports
import subprocess
import plotly.graph_objects as go
import pandas
import sys
import subprocess

app = Flask(__name__)


#### VARIABLES QUE SE PUEDEN MODIFICAR ###
loginPassword = "P32020"                                  # Contraseña para la interfaz web
arduinoPort = "ARDUINO"                                              # Puerto seleccionado por defecto
streamScript = "./mjpg-streamer.sh"                           # Ubicación del script para comenzar/detener la transmisión
soundFolder = "./v2/interface/static/sounds/"  # Ubicación de los reportes
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)      # Clave secreta usada para las cookies de la sesión
##########################################


pygame.mixer.init()

exitFlag = 0
arduinoActive = 0
streaming = 0
volume = 5
batteryLevel = -999
queueLock = threading.Lock()
workQueue = queue.Queue()
threads = []


#############################################
# Set up the multithreading stuff here
#############################################
# El segundo hilo será usado para enviar datos al microcontrolador
class arduino (threading.Thread):
	def __init__(self, threadID, name, q, port):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		self.q = q
		self.port = port
	def run(self):
		print("Starting Arduino Thread", self.name)
		process_data(self.name, self.q, self.port)
		print("Exiting Arduino Thread", self.name)

# Function to send data to the Arduino from a buffer queue
def process_data(threadName, q, port):
	global exitFlag

	ser = serial.Serial(port,115200)
	ser.flushInput()
	dataString = ""
	while not exitFlag:
		try:
			queueLock.acquire()
			if not workQueue.empty():
				data = q.get() + '\n'
				queueLock.release()
				ser.write(data.encode())
				print(data)
			else:
				queueLock.release()
			if (ser.inWaiting() > 0):
				data = ser.read()
				if (data.decode() == '\n' or data.decode() == '\r'):
					print(dataString)
					parseArduinoMessage(dataString)
					dataString = ""
				else:
					dataString += data.decode()
		# If an error occured in the Arduino Communication
		except Exception as e:
			print(e)
			exitFlag = 1
	ser.close()

# Function to parse messages received from the Arduino
def parseArduinoMessage(dataString):
	global batteryLevel

	# Battery level message
	if "Battery" in dataString:
		dataList = dataString.split('_')
		if len(dataList) > 1 and dataList[1].isdigit():
			batteryLevel = dataList[1]

# Turn on/off the Arduino Thread system
def onoff_arduino(q, portNum):
	global arduinoActive
	global exitFlag
	global threads
	global batteryLevel

	if not arduinoActive:
		# Set up thread and connect to Arduino
		exitFlag = 0

		usb_ports = [
			p.device
			for p in serial.tools.list_ports.comports()
		]

		thread = arduino(1, "Arduino", q, usb_ports[portNum])
		thread.start()
		threads.append(thread)

		arduinoActive = 1

	else:
		# Disconnect Arduino and exit thread
		exitFlag = 1
		batteryLevel = -999

		# Clear the queue
		queueLock.acquire()
		while not workQueue.empty():
			q.get()
		queueLock.release()

		# Join any active threads up
		for t in threads:
			t.join()

		threads = []
		arduinoActive = 0

	return 0


# Test whether the Arduino connection is still active
def test_arduino():
	global arduinoActive
	global exitFlag
	global workQueue

	if arduinoActive and not exitFlag:
		return 1
	elif exitFlag and arduinoActive:
		onoff_arduino(workQueue, 0)
	else:
		return 0


# Turn on/off the MJPG Streamer
def onoff_streamer():
	global streaming

	if not streaming:
		# Turn on stream
		subprocess.call([streamScript, 'start'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
		result = ""
		# Check whether the stream is on or not
		try:
			result = subprocess.call([streamScript, 'status'], stdout=subprocess.PIPE).stdout.decode('utf-8')
		except subprocess.CalledProcessError as e:
			result = e.output.decode('utf-8')
		print(result)

		if 'stopped' in result:
			streaming = 0
			return 1
		else:
			streaming = 1
			return 0

	else:
		# Turn off stream
		subprocess.call([streamScript, 'stop'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

		streaming = 0
		return 0


#############################################
# Flask Pages and Functions
#############################################

# Main Page
@app.route('/')
def index():
	if session.get('active') != True:
		return redirect(url_for('login'))

	# Get list of audio files
	files = []
	for item in sorted(os.listdir(soundFolder)):
		if item.endswith(".ogg"):
			audiofiles = os.path.splitext(os.path.basename(item))[0]

			# Set up default details
			audiogroup = "Other"
			audionames = audiofiles;
			audiotimes = 0;

			# Get item details from name, and make sure they are valid
			if len(audiofiles.split('_')) == 2:
				if audiofiles.split('_')[1].isdigit():
					audionames = audiofiles.split('_')[0]
					audiotimes = float(audiofiles.split('_')[1])/1000.0
				else:
					audiogroup = audiofiles.split('_')[0]
					audionames = audiofiles.split('_')[1]
			elif len(audiofiles.split('_')) == 3:
				audiogroup = audiofiles.split('_')[0]
				audionames = audiofiles.split('_')[1]
				if audiofiles.split('_')[2].isdigit():
					audiotimes = float(audiofiles.split('_')[2])/1000.0

			# Add the details to the list
			files.append((audiogroup,audiofiles,audionames,audiotimes))

	# Get list of connected USB devices
	ports = serial.tools.list_ports.comports()
	usb_ports = [
		p.description
		for p in serial.tools.list_ports.comports()
		#if 'ttyACM0' in p.description
	]
	# Ensure that the preferred Arduino port is selected by default
	selectedPort = 0
	for index, item in enumerate(usb_ports):
		if arduinoPort in item:
			selectedPort = index

	files = [('PdI', 'random path', 'Imágenes tomadas', '2020-09-02 15:12:55', '/imgViewer'),
	('Mediciones', 'random path', 'Temperatura', '2020-09-02 17:22:10', '/plotTemp'),
	('Mediciones', 'random path', 'Presión', '2020-09-02 16:15:32', 'plotPres'),
	('Rastreo', 'random path', 'Historial de ruta', '2020-09-03 22:45:21', 'plotMap')
	]
	return render_template('index.html',sounds=files, ports = usb_ports, portSelect = selectedPort, connected = 0)

# Login
@app.route('/login')
def login():
	if session.get('active') == True:
		return redirect(url_for('index'))
	else:
		return render_template('login.html')

# Login Request
@app.route('/login_request', methods = ['POST'])
def login_request():
	password = request.form.get('password')
	if password == loginPassword:
		session['active'] = True
		return redirect(url_for('index'))
	return redirect(url_for('login'))

# Motor Control
@app.route('/motor', methods=['POST'])
def motor():
	if session.get('active') != True:
		return redirect(url_for('login'))

	stickX =  request.form.get('stickX')
	stickY =  request.form.get('stickY')
	if stickX is not None and stickY is not None:
		xVal = int(float(stickX)*100)
		yVal = int(float(stickY)*100)
		print("Motors:", xVal, ",", yVal)
		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put("X" + str(xVal))
			workQueue.put("Y" + str(yVal))
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
	else:
		print("Error: No se pudo leer los datos del POST from motor command")
		return jsonify({'status': 'Error','msg':'No se pudo leer los datos del POST'})

# Update Settings
@app.route('/settings', methods=['POST'])
def settings():
	if session.get('active') != True:
		return redirect(url_for('login'))

	thing = request.form.get('type');
	value = request.form.get('value');

	if thing is not None and value is not None:
		if thing == "motorOff":
			print("Motor Offset:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("O" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
		elif thing == "steerOff":
			print("Steering Offset:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("S" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
		elif thing == "animeMode":
			print("Animation Mode:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("M" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
		elif thing == "soundMode":
			print("Sound Mode:", value)
		elif thing == "volume":
			global volume
			volume = int(value)
			print("Change Volume:", value)
		elif thing == "streamer":
			print("Turning on/off MJPG Streamer:", value)
			if onoff_streamer() == 1:
				return jsonify({'status': 'Error', 'msg': 'Unable to start the stream'})

			if streaming == 1:
				return jsonify({'status': 'OK','streamer': 'Active'})
			else:
				return jsonify({'status': 'OK','streamer': 'Offline'})
		elif thing == "shutdown":
			print("Shutting down Raspberry Pi!", value)
			result = subprocess.call(['sudo','nohup','shutdown','-h','now'], stdout=subprocess.PIPE).stdout.decode('utf-8')
			return jsonify({'status': 'OK','msg': 'Raspberry Pi is shutting down'})
		else:
			return jsonify({'status': 'Error','msg': 'No se pudo leer los datos del POST'})

		return jsonify({'status': 'OK' })
	else:
		return jsonify({'status': 'Error','msg': 'No se pudo leer los datos del POST'})

# Play Audio
@app.route('/audio', methods=['POST'])
def audio():
	if session.get('active') != True:
		return redirect(url_for('login'))

	clip =  request.form.get('clip')
	if clip is not None:
		clip = soundFolder + clip + ".ogg"
		print("Play music clip:", clip)
		pygame.mixer.music.load(clip)
		pygame.mixer.music.set_volume(volume/10.0)
		#start_time = time.time()
		pygame.mixer.music.play()
		#while pygame.mixer.music.get_busy() == True:
		#	continue
		#elapsed_time = time.time() - start_time
		#print(elapsed_time)
		return jsonify({'status': 'OK' })
	else:
		return jsonify({'status': 'Error','msg':'No se pudo leer los datos del POST'})

# Animate
@app.route('/animate', methods=['POST'])
def animate():
	if session.get('active') != True:
		return redirect(url_for('login'))

	clip = request.form.get('clip')
	if clip is not None:
		print("Animate:", clip)

		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put("A" + clip)
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
	else:
		return jsonify({'status': 'Error','msg':'No se pudo leer los datos del POST'})

# Servo Control
@app.route('/servoControl', methods=['POST'])
def servoControl():
	if session.get('active') != True:
		return redirect(url_for('login'))

	servo = request.form.get('servo');
	value = request.form.get('value');
	if servo is not None and value is not None:
		print("servo:", servo)
		print("value:", value)

		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put(servo + value)
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})
	else:
		return jsonify({'status': 'Error','msg':'No se pudo leer los datos del POST'})

# Arduino Connection
@app.route('/arduinoConnect', methods=['POST'])
def arduinoConnect():
	if session.get('active') != True:
		return redirect(url_for('login'))

	action = request.form.get('action');

	if action is not None:
		# Update drop-down selection with list of connected USB devices
		if action == "updateList":
			print("Reload list of connected USB ports")

			# Get list of connected USB devices
			ports = serial.tools.list_ports.comports()
			usb_ports = [
				p.description
				for p in serial.tools.list_ports.comports()
				#if 'ttyACM0' in p.description
			]

			# Ensure that the preferred Arduino port is selected by default
			selectedPort = 0
			for index, item in enumerate(usb_ports):
				if arduinoPort in item:
					selectedPort = index

			return jsonify({'status': 'OK','ports':usb_ports,'portSelect':selectedPort})

		# If we want to connect/disconnect Arduino device
		elif action == "reconnect":

			print("Reconnect to Arduino")

			if test_arduino():
				onoff_arduino(workQueue, 0)
				return jsonify({'status': 'OK','arduino': 'Disconnected'})

			else:
				port = request.form.get('port')
				if port is not None and port.isdigit():
					portNum = int(port)
					# Test whether connection to the selected port is possible
					usb_ports = [
						p.device
						for p in serial.tools.list_ports.comports()
					]
					if portNum >= 0 and portNum < len(usb_ports):
						# Try opening and closing port to see if connection is possible
						try:
							ser = serial.Serial(usb_ports[portNum],115200)
							if (ser.inWaiting() > 0):
								ser.flushInput()
							ser.close()
							onoff_arduino(workQueue, portNum)
							return jsonify({'status': 'OK','arduino': 'Conectado'})
						except:
							return jsonify({'status': 'Error','msg':'No se puede conectar al puerto serial seleccionado'})
					else:
						return jsonify({'status': 'Error','msg':'Puerto serial seleccionado inválido'})
				else:
					return jsonify({'status': 'Error','msg':'No se puede leer los datos del POST'})
		else:
			return jsonify({'status': 'Error','msg':'No se puede leer los datos del POST'})
	else:
		return jsonify({'status': 'Error','msg':'No se puede leer los datos del POST'})

# Se verifica el estado de la batería
@app.route('/arduinoStatus', methods=['POST'])
def arduinoStatus():
	if session.get('active') != True:
		return redirect(url_for('login'))

	action = request.form.get('type');

	if action is not None:
		if action == "battery":
			if test_arduino():
				return jsonify({'status': 'OK','battery':batteryLevel})
			else:
				return jsonify({'status': 'Error','msg':'Microcontrolador no conectado'})

	return jsonify({'status': 'Error','msg':'No se pudo leer los datos del POST'})

@app.route('/plotTemp')
def plotTemp():
    temp = pandas.read_csv('v2/interface/static/data/temperature.csv')
    time = temp['datetime']
    temperature = temp['Portland']
    layout = go.Layout(
        title="Datos históricos de temperatura",
        xaxis_title="hora",
        yaxis_title="temperatura"
    )

    fig = go.Figure(
        data=go.Scatter(x=time, y=temperature),
        layout=layout
    )
    fig.show()
    return redirect(url_for('index'))

@app.route('/plotPres')
def plotPres():
    temp = pandas.read_csv('v2/interface/static/data/pressure.csv')
    time = temp['datetime']
    temperature = temp['Portland']
    layout = go.Layout(
        title="Datos históricos de presión",
        xaxis_title="hora",
        yaxis_title="presión"
    )

    fig = go.Figure(
        data=go.Scatter(x=time, y=temperature),
        layout=layout
    )
    fig.show()
    return redirect('/')

@app.route('/plotMap')
def plotMap():
    df = pandas.read_csv('v2/interface/static/data/GPS.csv')
    fig = go.Figure(go.Scattermapbox(
    mode = "markers+lines",
    lon = df['longitude'].tolist(),
    lat = df['latitude'].tolist(),
    marker = {'size': 10}))

    fig.update_layout(
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'center': {'lon': -57, 'lat': -25},
            'style': "stamen-terrain",
            'zoom': 6})

    fig.show()
    return redirect('/')

@app.route('/imgViewer')
def openImage():
    imageViewerFromCommandLine = {'linux':'xdg-open',
                                  'win32':'explorer',
                                  'darwin':'open'}[sys.platform]
    subprocess.run([imageViewerFromCommandLine, 'v2/interface/static/data/img/'])
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
