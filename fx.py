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

