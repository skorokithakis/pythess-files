import SimpleHTTPServer
import SocketServer
import kivy
kivy.require('1.9.1') # replace with your current kivy version !
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.label import Label
import socket

# first find out the IP your phone has
ip = ([(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1])
PORT = 8008 # the port to serve
msg = "serving at port" + str(ip)+':'+ str(PORT) # the msg to display
#somehing like "serving at port 192.168.1.1:8008" so we know the address to put in our browser

def my_callback(instance):
	"""
		This is the lighter version of a simple Python http server
	"""
	Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
	httpd = SocketServer.TCPServer(("", PORT), Handler)
	httpd.serve_forever() # this blocks our main thread to avoid we use Clock 'see below'

# to avoid blocking the main thread schedule to run the server 5 seconds after the app starts
Clock.schedule_once(my_callback, 5)

class MyApp(App):
	"""
		The main app, just return a label with our msg ex. "serving at port 192.168.1.1:8008"
	"""
	def build(self):
		return Label(text=msg)


if __name__ == '__main__':
    MyApp().run()
