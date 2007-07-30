#! /usr/bin/python

from tp.netlib import Connection
from tp.netlib import failed, constants, objects
from tp.netlib.client import url2bits
from tp.client.cache import Cache

version = (0, 0, 1)

cache      = None
connection = None

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
		if value == 'ref':
			raise SyntaxError('This should not happen!')

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

# FIXME: These should be defined in a "profile" somewhere as they are all server specific...
PLANET_TYPE = 3
FLEET_TYPE  = 4

MOVE_ORDER     = 1
BUILD_ORDER    = 2
COLONISE_ORDER = 3
MERGE_ORDER    = 5

FRIGATE_SPEED    = 200000000
BATTLESHIP_SPEED = 300000000

FRIGATE_BUILD    = 2
BATTLESHIP_BUILD = 6

FRIGATE_POWER    = 0.2
BATTLESHIP_POWER = 1

MARGIN = 10

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

		power = 0

		assets = [[self.ref], self.ref][isinstance(self.ref, list)]
		for asset in assets:
			if asset._subtype == FLEET_TYPE:
				for shipid, num in asset.ships:
					# Scouts do nothing!
					if cache.designs[shipid].name == 'Scout':
						continue				
	
					# Frigates...
					if cache.designs[shipid].name == 'Frigate':
						power += FRIGATE_POWER*num
						continue

					if cache.designs[shipid].name == 'Battleship':
						# Battleships
						power += BATTLESHIP_POWER*num
						continue

					print "WARNING! Unknown ship type!"

		return power

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
		power = 0

		threats = [[self.ref], self.ref][isinstance(self.ref, list)]
		for threat in threats:
			if threat._subtype == PLANET_TYPE:
				# Check if this is a homeworld
				if False:
					power += BATTLESHIP_POWER*5
				else:
					power += BATTLESHIP_POWER*2

			if threat._subtype == FLEET_TYPE:
				for shipid, num in threat.ships:
					# Scouts do nothing!
					if cache.designs[shipid].name == 'Scouts':
						continue				
	
					# Frigates...
					if cache.designs[shipid].name == 'Frigate':
						power += FRIGATE_POWER*num
						continue

					# Battleships or unknown...
					power += BATTLESHIP_POWER*num

		return power

class Neutral(Asset, Threat):
	"""\
	A Neutral object is anything which could possibly be an asset or a threat to the computer.
	"""
	pass

class Task(Reference):
	"""\
	A thing which needs to be done.
	"""
	def __init__(self, ref):
		if self.__class__ == Task:
			raise SyntaxError("Can not instanciate base Task class!")

		if not isinstance(ref, Reference):
			raise TypeError("Task's reference must be a Reference object.")

		## Actual method...
		Reference.__init__(self, ref)

		self.assigned = []
		if isinstance(ref, Task):
			if ref.long() < float('inf'):
				self.assigned.append((ref.long(), ref, ref.portion()))

	def task(self):
		return self.__class__
	task = property(task)

	def long(self):
		"""
		Long returns how long this task will take to complete in turns.
		"""
		if len(self.assigned) > 0:
			return self.assigned[-1][0]
		return float('inf')

	def portion(self):
		portion = 0
		for soon, asset, asset_portion in self.assigned:
			portion += asset_portion
		return portion

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

		print self.assigned

		for i, (soon, asset, asset_portion) in enumerate(self.assigned):
			portion += asset_portion

			if portion >= 100:
				break

		i += 1

		leftover = self.assigned[i:]
		del self.assigned[i:]
		return leftover

	def __str__(self, short=False):
		t = ""
		if isinstance(self.ref, Task):
			t += repr(object.__repr__(self.ref))
		else:
			t += str(self.ref)

		if len(self.assigned) > 0:
			s = ""
			if short:
				s += "[...]"
			else:
				s += "["
				if False and len(self.assigned) < 4:
					for soon, asset, portion in self.assigned:
						if isinstance(asset, Task):
							s += "(%.2f, %s, %.1f), " % (soon, asset.__str__(short=True), portion)
						else:
							s += "(%.2f, %s, %.1f), " % (soon, asset, portion)
				else:
					for soon, asset, portion in self.assigned:
						if isinstance(asset, Task):
							s += "\n\t(%.2f, %s, %.1f), " % (soon, asset.__str__(short=True), portion)
						else:
							s += "\n\t(%.2f, %s, %.1f), " % (soon, asset, portion)
				s = s[:-2] +"]"

			return "<Task %s - %s ((%.0f%%) assigned to %s)>" % (self.name, t, self.portion(), s)
		else:
			return "<Task %s - %s (unassigned)>" % (self.name, t)
	__repr__ = __str__

	def issue(self):
		"""\
		Issue the correct orders to the assigned assets..
		"""
		used_assets = []

		# First job is to collect all the assets together
		flagship = self.assigned[0][1]
		if len(self.assigned) > 1:
			used_assets.append(flagship)

			for soon, asset, portion in self.assigned[1:]:
				used_assets.append(asset)

				results = []

				OrderAdd_Move(asset,  flagship.ref.pos, results)
				OrderAdd_Merge(asset, flagship,         results)
				OrderPrint(asset, results)

		return used_assets

	def requirements(self, asset):
		"""\
		Issues the correct orders to fufill this task..
		"""
		raise SyntaxError("This task doesn't impliment the requirements order!")

class TaskDestroy(Task):
	name = 'Destroy '

	def issue(self):
		"""\
		Issue the correct orders to the assigned assets..
		"""
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position

		if len(self.assigned) == 1:
			flagship = self.assigned[0][1]
			used_assets.append(flagship)

			# Only actually go after the object if we can complete the task!
			if self.portion() >= 100:
				results = []
				# FIXME: Should actually try an intercept the target!
				OrderAdd_Move(flagship, self.ref.ref.pos, results)
				OrderPrint(flagship, results)

		return used_assets

class TaskColonise(Task):
	name = 'Colonise'

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.assigned) == 1:
			flagship = self.assigned[0][1]
			used_assets.append(flagship)

			results = []
			OrderAdd_Move(flagship, self.ref.ref.pos, results)
			OrderAdd_Colonise(flagship, self.ref, results)
			OrderPrint(flagship, results)

		return used_assets

class TaskTakeOver(TaskColonise):
	name = 'TakeOver'

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.assigned) == 1:
			flagship = self.assigned[0][1]
			used_assets.append(flagship)

			# Only actually go after the object if we can complete the task!
			if self.portion() >= 100:
				results = []
				OrderAdd_Move(flagship, self.ref.ref.pos, results)
				OrderAdd_Colonise(flagship, self.ref, results)
				OrderPrint(flagship, results)

		return used_assets


class TaskBuild(Task):
	name = 'Build   '

	def issue(self):
		used_assets = []

		for soon, asset, portion in self.assigned:
			used_assets.append(asset)

			results = []

			# Remove current orders...
			connection.remove_orders(asset.ref.id, range(0, asset.ref.order_number))

			result = connection.insert_order(asset.ref.id, -1, BUILD_ORDER, [], [], 0, "")
			result = connection.get_orders(asset.ref.id, 0)
			ships = {}
			for id, name, max in result[0].ships[0]:
				ships[name] = id
			connection.remove_orders(asset.ref.id, [0]) 
			
			if self.ref.task == Task.COLONISE:
				# If we are referencing a colonise, better build a frigate
				print "Issuing orders to %s to build a frigate" % (asset,)
				results.append(connection.insert_order(asset.ref.id, -1, BUILD_ORDER, [], [(ships['Frigate'],1)], 0, "A robot army!"))
			if self.ref.task == Task.DESTROY:
				# Better build a battleship
				print "Issuing orders to %s to build a battleship" % (asset,)
				results.append(connection.insert_order(asset.ref.id, -1, BUILD_ORDER, [], [(ships['Battleship'],1)], 0, "A robot army!"))
			if self.ref.task == Task.TAKEOVER:
				# Better build a battleship and a frigate
				print "Issuing orders to %s to build a battleship and frigate" % (asset,)
				results.append(connection.insert_order(asset.ref.id, -1, BUILD_ORDER, [], [(ships['Frigate'],1), (ships['Battleship'],1)], 0, "A robot army!"))

			OrderPrint(asset, results)

		return used_assets

	def long(self):
		return self.ref.long()

	def portion(self):
		return self.ref.portion()

	def assign(self, soon, asset, portion=100):
		"""
		Assign an asset to this task.

		Soon is how soon this asset will complete it's "portion" of the task.

		Adding a new asset which would take the number of assets working on
		the task above 100% will cause the method to return a list of
		assets which are no longer needed.
		"""
		a = Task.assign(self, soon, asset, portion)
	
		if len(a) != 0:
			print "---------->", a

		return self.ref.assign(soon, asset, portion)


# FIXME: Better way to do this...
Task.DESTROY  = TaskDestroy
Task.COLONISE = TaskColonise
Task.TAKEOVER = TaskTakeOver
Task.BUILD 	  = TaskBuild
Task.types = (Task.DESTROY, Task.COLONISE, Task.TAKEOVER, Task.BUILD)

def OrderPrint(asset, results):
	"""\
	Print out the results array..
	"""
	if len(results) == 0:
		print
		return

	for i, result in enumerate(results):
		#print result
		if not result[0]:
			raise IOError("Wasn't able to issue an order for some reason! %s" % repr(result))

		# Order should complete in
		result = connection.get_orders(asset.ref.id, i)
		if not result[0]:
			raise IOError("Wasn't able to issue an order for some reason! %s" % repr(result))
		print "Order %i will complete in %.2f turns" % (i, result[0].turns)
	print

def OrderAdd_Move(asset, pos, results):
	"""\
	This function issues orders for the asset to move to the given position.

	It won't add any orders if the asset is at the given position.
	"""
	if asset.ref.pos == pos:
		return

	# FIXME: Check that asset can move!

	while True:
		onum = len(results)

		# Check if the asset already has this order
		if asset.ref.order_number > onum:
			order = cache.orders[asset.ref.id][onum]
			
			# Remove the order if it isn't a move order
			if order.subtype != MOVE_ORDER:
				print "Move order - Current order wasn't a move order!"
				# FIXME: Should check the return result of this command
				connection.remove_orders(asset.ref.id, [onum])
				asset.ref.order_number -= 1
				continue

			# Remove the order if it isn't a move order to the correct location
			if order.pos != pos:
				print "Move order - Current order was to wrong destination!"
				# FIXME: Should check the return result of this command
				connection.remove_orders(asset.ref.id, [onum])
				asset.ref.order_number -= 1
				continue

			# Order is correct
			print "Move order - Object already had correct move order."
			results.append((True, 'Already existed...'))
			break
		else:
			print "Move order - Issuing new order to %s move %s" % (asset, pos)
			# We need to issue a move order instead.
			results.append(connection.insert_order(asset.ref.id, -1, MOVE_ORDER, pos))
			asset.ref.order_number += 1
			break

def OrderAdd_Colonise(asset, target, results):
	# FIXME: Check that target is a planet!

	while True:
		onum = len(results)
		if asset.ref.order_number > onum:
			order = cache.orders[asset.ref.id][onum]

			# Remove the order if it isn't a move order
			if order.subtype != COLONISE_ORDER:
				print "Colonise order - Current order wasn't a colonise order!"
				# FIXME: Should check the return result of this command
				connection.remove_orders(asset.ref.id, [onum])
				asset.ref.order_number -= 1
				continue

			# Order is correct
			print "Colonise order - Object already had correct colonise order."
			results.append((True, 'Already existed...'))
			break
		else:
			print "Colonise order - Issuing orders to %s colonise %r" % (asset, target.ref)
			# We need to issue a move order instead.
			results.append(connection.insert_order(asset.ref.id, -1, COLONISE_ORDER)) #, target.ref.id))
			asset.ref.order_number += 1
			break

def OrderAdd_Merge(asset, target, results):
	# FIXME: Check that asset and target are both Fleets!

	while True:
		onum = len(results)
		if asset.ref.order_number > onum:
			order = cache.orders[asset.ref.id][onum]

			# Remove the order if it isn't a move order
			if order.subtype != MERGE_ORDER:
				print "Merge order - Current order wasn't a MergeFleet order!"
				# FIXME: Should check the return result of this command
				connection.remove_orders(asset.ref.id, [onum])
				asset.ref.order_number -= 1
				continue

			#if order.target != target.ref.id:
			#	print "Merge order - Current order didn't target correct object!"
			#	# FIXME: Should check the return result of this command
			#	connection.remove_orders(asset.ref.id, [onum])
			#	asset.ref.order_number -= 1
			#	continue

			# Order is correct
			print "Merge order - Object already had correct MergeFleet order."
			results.append((True, 'Already existed...'))
			break
		else:
			print "Merge order - Issuing orders to %s merge with %r" % (asset, target.ref)
			# We need to issue a move order instead.
			results.append(connection.insert_order(asset.ref.id, -1, MERGE_ORDER))
			asset.ref.order_number += 1
			break

