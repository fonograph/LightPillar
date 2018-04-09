import serial
import pygame
import time

# Initialize Pygame.
pygame.init()
# Set size of pygame window.
screen=pygame.display.set_mode((640,480))
# Create empty pygame surface.
background = pygame.Surface(screen.get_size())
# Fill the background white color.
background.fill((255, 255, 255))
# Convert Surface object to make blitting faster.
background = background.convert()
# Copy background to screen (position (0, 0) is upper left corner).
screen.blit(background, (0,0))
# Create Pygame clock object.  
clock = pygame.time.Clock()

mainloop = True
# Desired framerate in frames per second. Try out other values.              
FPS = 30
# How many seconds the "game" is played.
playtime = 0.0

serial = serial.Serial('/dev/cu.usbmodem1451', 250000)

time.sleep(2)

while mainloop:
	# Do not go faster than this framerate.
	milliseconds = clock.tick(FPS) 
	playtime += milliseconds / 1000.0 

	for i in range(4):
		data = bytes([1 for j in range(210)])
		serial.write(data)
		#print(i, len(data))
		serial.readline()
	
	for event in pygame.event.get():
		# User presses QUIT-button.
		if event.type == pygame.QUIT:
			mainloop = False 
		elif event.type == pygame.KEYDOWN:
			# User presses ESCAPE-Key
			if event.key == pygame.K_ESCAPE:
				mainloop = False
				
	# Print framerate and playtime in titlebar.
	text = "FPS: {0:.2f}   Playtime: {1:.2f}".format(clock.get_fps(), playtime)
	pygame.display.set_caption(text)

	#Update Pygame display.
	pygame.display.flip()

# Finish Pygame.  
pygame.quit()



