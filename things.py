#! /usr/bin/python

from tp.netlib import Connection
from tp.netlib import failed, constants, objects
from tp.netlib.client import url2bits
from tp.client.cache import Cache

version = (0, 0, 1)

import math

class Reference(object):
	"""\
	Something which refers to something else.
	"""
	def __init__(self, ref):
		self.ref = ref

	def __str__(self):
		return "<%s ref=%r>" % (self.__class__.__name__, self.ref)
	__repr__ = __str__

	def __getattr__(self, value):
		class Proxy(object):
			"""\
			This proxy class lets you use the following idiom,

			Say you create a reference which points to a list of objects,
			a = Reference([obj1, obj2])

			If both either obj1 or obj2 has an attribue "subtype" with value COLONISE,
			you can do:

			>>> class obj:
			>>> 	pass
			>>>
			>>> obj1 = obj()
			>>> obj2 = obj()
			>>> obj1.subtype = COLONISE
			>>> obj1.orders = [COLONISE, 19]
			>>> obj2.subtype = OTHER
			>>> obj2.orders = [78, OTHER]
			>>> r = Reference([obj1, obj2])

			>>> COLONISE in r.subtype
			True
	
			>>> 22 in r.subtype
			False

			>>> 78 in r.other
			True

			>>> 100 in r.other
			False
			"""
			def __init__(self, base, name):
				self.base = base
				self.name = name

			def __contains__(self, value):
				base = self.base
				name = self.name
				if not isinstance(base.ref, (list, tuple)):
					attrib = getattr(base.ref, name)
					if isinstance(attrib, (list, tuple)):
						return value in attrib
					else:
						return value == attrib
				else:
					# Check all the objects that this thing references
					for x in base.ref:
						attrib = getattr(x, name)
						if isinstance(attrib, (list, tuple)):
							if value in attrib:
								return True
						else:
							if value == attrib:
								return True
					return False
		return Proxy(self, value)

class Asset(Reference):
	"""\
	An asset is anything which has value to the computer.
	"""

	def power(self):
		"""\
		Returns how powerful an object is.
		"""
		# A Planet is always has no power
		# A fleet is as powerful as the sum of it parts
		return 10

class Threat(Reference):
	"""\
	A threat is anything which could possibly hurt the computer.
	"""

	def threat(self):
		"""\
		This function returns two values.

		The first value is how threatening the object is in "absolute" terms.
		The second value is how soon this threat must be delt with.
		"""
		# Planets are more threatening but can be dealt with over a longer period of time
		# Ships are less threatening but are more urgent
		#	Unarmed ships are ignored
		#   Big groups of ships are more important
		# Threats which are closer to assets are more threatening
		pass

	def power(self):
		"""\
		Returns how powerful an object is.
		"""
		# A planet is equal to x plus a fudge factor
		# A fleet is equal to the sum of its parts
		#   plus a "reinforment factor" of other close by threats
		return 10

class Neutral(Asset, Threat):
	"""\
	A Neutral object is anything which could possibly be an asset or a threat to the computer.
	"""
	pass

class Task(Reference):
	"""\
	A thing which needs to be done.
	"""
	DESTROY  = 'Destroy '
	COLONISE = 'Colonise'
	TAKEOVER = 'TakeOver'
	BUILD 	 = 'Build   '
	types = (DESTROY, COLONISE, TAKEOVER, BUILD)

	def __init__(self, type, ref):
		## Error checking....
		if not (type in Task.types):
			raise TypeError("Task's type was not valid!")

		if not isinstance(ref, Reference):
			raise TypeError("Task's reference must be a Reference object.")

		## Actual method...
		self.task = type
		Reference.__init__(self, ref)

		self.assigned = []

	def long(self):
		"""
		Long returns how long this task will take to complete in turns.
		"""
		if len(self.assigned) > 0:
			return self.assigned[-1][0]
		return float('inf')

	def assign(self, soon, asset, portion=100):
		"""
		Assign an asset to this task.

		Soon is how soon this asset will complete it's "portion" of the task.

		Adding a new asset which would take the number of assets working on
		the task above 100% will cause the method to return a list of
		assets which are no longer needed.
		"""
		## Error checking....
		if not isinstance(soon, float):
			try:
				soon = float(soon)
			except:
				raise TypeError("Assign's 'soon' argument must be a float.")

		if not isinstance(portion, float):
			try:
				portion = float(portion)
			except:
				raise TypeError("Assign's 'portion' argument must be a float.")

		if not isinstance(asset, Reference):
			raise TypeError("Assign's asset must be a Reference object.")
		if self == asset:
			raise TypeError("Can not be assigned to oneself...")

		## Actual method...
		self.assigned.append((soon, asset, portion))
		self.assigned.sort()

		portion = 0
		for i, (soon, asset, asset_portion) in enumerate(self.assigned):
			portion += asset_portion

			if portion >= 100:
				break

		i += 1

		leftover = self.assigned[i:]
		del self.assigned[i:]
		return leftover

	def __str__(self):
		if len(self.assigned) > 0:
			return "<Task %s - %s (assigned to %r)>" % (self.task, self.ref, self.assigned)
		else:
			return "<Task %s - %s (unassigned)>" % (self.task, self.ref)
	__repr__ = __str__

if __name__ == "__main__":
	run()

