import random

class FX(object):

	def __init__(self):
		self.frame = 0

	def update(self):
		self.frame += 1


class FXPulse(FX):

	def __init__(self, color):
		FX.__init__(self)
		self.color = color

	def update(self):
		FX.update(self)

	def getPixel(self, i):
		frame = self.frame % 60
		if frame > 30:
			frame = 60 - frame
		alpha = frame/30
		return (round(self.color[0]*alpha), round(self.color[1]*alpha), round(self.color[2]*alpha))

class FXStartup(FX):

	def __init__(self):
		FX.__init__(self)
		self.stage = 0
		self.stageInc = 30
		self.nextStage = self.frame + self.stageInc
		self.pixels = [(0,0,0)] * 1000

	def update(self):
		FX.update(self)
		if self.frame == self.nextStage:
			self.stage += 1
			self.stageInc -= 1
			if self.stageInc == 0:
				self.stageInc = 1
			self.nextStage = self.frame + self.stageInc

			p = self.stage / 20
			for i in range(len(self.pixels)):
				if random.random() < p:
					self.pixels[i] = randomColor()
				else:
					self.pixels[i] = (0,0,0)

	def getPixel(self, i):
		return self.pixels[i]


def randomColor():
	points = 255
	r = random.randint(0, points)
	points -= r
	g = random.randint(0, points)
	points -= g
	b = points
	return (r,g,b)
