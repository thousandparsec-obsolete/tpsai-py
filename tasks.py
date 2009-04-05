
import server
from things import Reference, Asset, OrderCreate, OrderRemove, dist

"""

Task Requirements
-------------------------------------------------------------------------------
A Task requires a bunch of assets to be completed. Assets fall into two
categories when acting on a task.

 * primary role assets,

These are the assets which are required to make the task occur. A task can
not be completed unless all the primary roles can be met. Normally only one
asset is need to fulfill each primary role (any other assets are put in the
auxiliary pile).

For example:
 - A frigate is required to complete a takeover order.

 * auxiliary assets

These are assets which can help the asset be completed. These assets may
either be unable to complete the task by themselves, or excess of a primary
type.

For example:
  - A battleship can no fulfill a TakeOver order by itself. It can however
    provide support.
  - If there is already a frigate in a TakeOver order, any other frigate
    assets are auxiliary assets.

The Flagship
-------------------------------------------------------------------------------
Each Task has a "flagship" this is the asset all other assets will collect
at before starting on the task.

The flagship is normally the closest asset to where the task location (IE
the place that it needs to be completed at). 

If a fleet asset is too close to the task it won't be considered to be the
flagship.

The flagship will remain stationary until all assets have merged with it.
"""

class Role(object):
	"""
	A role that must be fulfilled for a task to be completed.

	"""

	def __init__(self):
		self.fulfilment = None

	def assign(self, f):
		# FIXME: This does not work with an asset which must have multiple roles fulfilled.
		if not isinstance(f, Task.Fulfilment):
			raise TypeError("Can only assign a fulfilment")

		# Check that the asset can fulfil this role?
		if self.check(f):
			# Has any other asset been assigned to this role?
			if self.fulfilment is None:
				self.fulfilment = f
				return None

			# Can this asset fulfil this role sooner?
			if f.soon < self.fulfilment.soon:
				self.fulfilment, f = f, self.fulfilment
			
		return f

	def unassign(self):
		f = self.fulfilment
		self.fulfilment = None

		return f

class Coloniser(Role):
	"""
	This object which fulfils this role will be used to colonise the
	planet.
	"""
	def check(self, f):
		# Check that the object can colonise a planet...		
		return server.COLONISE_ORDER in f.asset.ref.order_types or not f.direct


class Task(Reference):
	"""\
	A thing which needs to be done.
	"""
	class Fulfilment(object):
		"""\
		Fulfilment class contains a 'request' to fulfill a certain task.

		asset,		The asset which is going to fulfill the task
		soon,		How long it will take for the asset to fulfill the task
		portion, 	The portion of this task this asset can complete
		direct,		Can asset can directly fulfill the task?
		"""
		def __init__(self, asset, soon, portion=100.0, direct=True):
			## Error checking....
			if not isinstance(soon, float):
				try:
					soon = float(soon)
				except:
					raise TypeError("Fulfilment's 'soon' argument must be a float.")

			if not isinstance(portion, float):
				try:
					portion = float(portion)
				except:
					raise TypeError("Fulfilment's 'portion' argument must be a float.")

			if not isinstance(direct, bool):
				raise TypeError("Fulfilment's 'direct' argument must be a bool.")

			if not isinstance(asset, Asset):
				raise TypeError("Fulfilment's 'asset' argument must be a Asset object.")

			self.soon    = soon
			self.asset   = asset
			self.portion = portion
			self.direct  = direct

		def __str__(self):
			if self.direct:
				brackets = " [%s]"
			else:
				brackets = " {%s}"
			return brackets % ("%s in %.2f turns will complete %.2f%%" % (self.asset.__str__(True), self.soon, self.portion))
		__repr__ = __str__

		def __cmp__(self, other):
			"""
			Fuilfilments are compared by how long the fulfilment will take,
			and then by the portion of the task they will fulfull.
			"""
			if not isinstance(other, Task.Fulfilment):
				raise TypeError("Don't know how to compare these types?")
			return cmp((self.soon, self.portion), (other.soon, other.portion))

	def __init__(self, ref, roles=[]):
		if self.__class__ == Task:
			raise SyntaxError("Can not instantiate base Task class!")

		if not isinstance(ref, Reference):
			raise TypeError("Task's reference must be a Reference object.")

		## Actual method...
		Reference.__init__(self, [ref])

		## The primary role fulfilments
		self.roles     = roles
		## The auxiliary fulfilments
		self.auxiliary = []

	def __eq__(self, other):
		"""
		Too tasks are equal if they refer to the same thing.
		"""
		if not isinstance(other, Task):
			return False
		return self.ref == other.ref

	def __neq__(self, other):
		return not self.__eq__(other)

	def __cmp__(self, other):
		"""
		Tasks are compared by the portions completed.
		"""
		if self == other:
			return 0
		return cmp(self.portion(), other.portion())

	def ref(self):
		return self.refs[0]
	ref = property(ref)

	def type(self):
		return self.__class__
	type = property(type)

	def long(self):
		"""
		How long this task will take to complete in turns.
		"""
		l = -1

		# Take the maximum of the auxiliary 
		if len(self.auxiliary) > 0:
			l = self.auxiliary[-1].soon

		# Make sure that none of the roles will take longer
		for role in self.roles:
			if role.fulfilment is None:
				continue
			l = max(l, role.fulfilment.soon)

		if l == -1:
			return float('inf')
		return l

	def fulfilments(self):
		"""
		Returns all the fulfilments (include ones in roles and auxiliary).
		"""
		return self.auxiliary+[role.fulfilment for role in self.roles if not role.fulfilment is None]

	def portion(self):
		"""
		The portion of this Task which has been fulfilled.
		"""
		portion = 0

		for fulfilment in self.auxiliary:
			portion += fulfilment.portion

		# Have all the roles been fulfilled?
		rolesfulfilled = True
		for role in self.roles:
			if role.fulfilment is None:
				rolesfulfilled = False
			else:
				portion += role.fulfilment.portion

		# If they haven't the maximum the portion is 99%
		if not rolesfulfilled:
			portion = min(portion, 99)

		return portion

	def assign(self, fulfilment):
		"""
		Assign an asset to this task.

		Soon is how soon this asset will complete it's "portion" of the task.

		Adding a new asset which would take the number of assets working on
		the task above 100% will cause the method to return a list of
		assets which are no longer needed.
		"""
		## Error checking....
		if not isinstance(fulfilment, Task.Fulfilment):
			raise TypeError("Assign's argument must be a Fulfilment object.")
		if self == fulfilment.asset:
			raise TypeError("Can not be auxiliary to oneself...")

		# Try assign the fulfilment to a role
		portion = 0
		for role in self.roles:
			if not fulfilment is None:
				fulfilment = role.assign(fulfilment)

			if not role.fulfilment is None:
				portion += role.fulfilment.portion

		# Else assign the fulfilment to a auxiliary role
		if not fulfilment is None:
			self.auxiliary.append(fulfilment)
			self.auxiliary.sort()

		# Remove any excess auxiliary assets
		i = 0
		while portion < 100 and i < len(self.auxiliary):
			portion += self.auxiliary[i].portion
			i += 1	
		leftover = self.auxiliary[i:]
		del self.auxiliary[i:]

		# Return any excess assets
		return [fulfilment.asset for fulfilment in leftover]

	def unassign(self):
		fulfilments = self.fulfilments()

		# Unassign the roles
		for role in self.roles:
			role.unassign()

		# Unassign the auxiliary positions
		self.auxiliary = []

		return fulfilments

	def __str__(self, short=False):
		if short:
			if len(self.fulfilments()) > 0:
				return "<Task %s - %s (%.0f%%)>" % (self.name, self.ref, self.portion())
			else:
				return "<Task %s - %s (unassigned)>" % (self.name, self.ref)
		
		# Add the fulfilments to given roles
		s = "\n"
		for role in self.roles:
			s += "\t%s:\t%s,\n" % (role.__class__.__name__, role.fulfilment)

		# Add any auxiliary fulfilments
		if len(self.auxiliary) > 0:
			s += "\tAuxiliary:\t%s, " % self.auxiliary[0]
			for fulfilment in self.auxiliary[1:]:
				s+= "\n\t\t\t%s, " % fulfilment
			s = s[:-2] + "\n"
		return "<Task %s - %s\n  %.0f%% assigned to %s>" % (self.name, self.ref, self.portion(), s[:-1])
	__repr__ = __str__

	def flagship(self):
		"""
		Returns the flagship for the fleet which will fulfil the task.
		Also returns if this flagship has yet to be built.

		(asset, built?)
		"""
		distances = {}

		for fulfilment in self.fulfilments():
			distances[dist(fulfilment.asset.ref.pos, self.ref.pos[0])] = (fulfilment.asset, fulfilment.direct)

		keys = distances.keys()
		keys.sort()

		# Don't want to assemble too close to the target!
		# FIXME: If we are orbiting a planet, probably safe to use this ship...
		while len(keys) > 1:
			if keys[0] > server.ASSEMBLE_DISTANCE:
				break
			keys.pop(0)

		return distances[keys[0]]

	def issue(self):
		"""\
		Issue the correct orders to the assigned assets..
		"""
		used_assets = []

		# First job is to collect all the assets together
		if len(self.fulfilments()) > 1 or self.portion() < 100:
			# Find the flagship
			flagship, flagbuilt = self.flagship()
			print "Flagship is", flagship, "assembling at", flagship.pos[0]
			print

			for fulfilment in self.fulfilments():
				used_assets.append(fulfilment.asset)

				print "Orders for", fulfilment.asset.__str__(True)
				orders = []
				if fulfilment.direct:
					orders.append(Order_Move(fulfilment.asset, flagship.pos[0], slot))
					if flagbuilt:
						orders.append(Order_Merge(fulfilment.asset, flagship, slot))
				else:
					orders.append(Order_Build(fulfilment.asset, self, slot))
				
				OrderPrint(fulfilment.asset)

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
		if len(self.fulfilments()) == 1 and self.portion() >= 100:
			fulfilment = self.fulfilments()[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			orders = []
			if fulfilment.direct:
				# FIXME: Should actually try an intercept the target!
				orders.append(Order_Move(fulfilment.asset, self.ref.pos[0]))
			else:
				orders.append(Order_Build(fulfilment.asset, self))

			OrderPrint(fulfilment.asset)

		return used_assets

class TaskColonise(Task):
	name = 'Colonise'

	def __init__(self, ref):
		Task.__init__(self, ref, [Coloniser()])

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.fulfilments()) == 1 and self.portion() >= 100:
			fulfilment = self.fulfilments()[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			orders = []
			if fulfilment.direct:
				orders.append(Order_Move(fulfilment.asset, self.ref.pos[0]))
				orders.append(Order_Colonise(fulfilment.asset, self.ref))
			else:
				orders.append(Order_Build(fulfilment.asset, self))

			OrderPrint(fulfilment.asset)

		return used_assets

class TaskTakeOver(TaskColonise):
	name = 'TakeOver'

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.fulfilments()) == 1 and self.portion() >= 100:
			fulfilment = self.fulfilments()[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			orders = []
			if fulfilment.direct:
				orders.append(Order_Move(fulfilment.asset, self.ref.pos[0]))
				orders.append(Order_Colonise(fulfilment.asset, self.ref))
			else:
				orders.append(Order_Build(fulfilment.asset, self))

			OrderPrint(fulfilment.asset)

		return used_assets

# FIXME: Better way to do this...
Task.DESTROY  = TaskDestroy
Task.COLONISE = TaskColonise
Task.TAKEOVER = TaskTakeOver
Task.types = (Task.DESTROY, Task.COLONISE, Task.TAKEOVER)

def OrderPrint(asset):
	"""\
	Print out the order completion time...
	"""
	for i, order in enumerate(server.cache.orders[asset.ref.id]):
		print "Order %i will complete in %.2f turns (%r)" % (i, order.turns, order)
	print

def Order_Move(asset, pos, slot):
	"""\
	This function issues orders for the asset to move to the given position.

	It won't add any orders if the asset is at the given position.
	"""
	if asset.ref.pos == pos:
		print "Move Order     - Object already at destination!"
		return False

	# FIXME: Check that asset can move!

	oid = asset.ref.id
	while True:
		# Check if the asset already has this order
		if asset.ref.order_number > slot:
			order = server.cache.orders[oid][slot]
			
			# Remove the order if it isn't a move order
			if order.subtype != server.MOVE_ORDER:
				print "Move order     - Current order (%r) wasn't a move order!" % order
				OrderRemove(oid, slot)
				continue

			# Remove the order if it isn't a move order to the correct location
			if order.pos != pos:
				print "Move order     - Current order (%r) was too wrong destination!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Move order     - Already had correct move order."
			break
		else:
			print "Move order     - Issuing new order to move too %s" % (pos,)
			# We need to issue a move order instead.
			OrderCreateAfter(oid, -1, server.MOVE_ORDER, pos)
			break
	return True

def Order_Colonise(asset, targets, slot):
	# Find the planet which we want to colonise
	target = None
	for ref in targets.refs:
		if ref._subtype == server.PLANET_TYPE:
			target = ref
			break
	if target is None:
		raise TypeError("Trying to colonise something which isn't a planet!")

	oid = asset.ref.id
	while True:
		if asset.ref.order_number > slot:
			order = server.cache.orders[oid][slot]

			# Remove the order if it isn't a colonise order
			if order.subtype != server.COLONISE_ORDER:
				print "Colonise order - Current order (%r) wasn't a colonise order!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Colonise order - Already had correct colonise order (%r)." % (target,)
			break
		else:
			print "Colonise order - Issuing new order colonise %r" % (target,)
			# We need to issue a move order instead.
			OrderCreateAfter(oid, -1, server.COLONISE_ORDER, target.id)
			break

	return True

def Order_Merge(asset, target, slot):
	# FIXME: Check that asset and target are both Fleets!
	if asset.ref.id == target.ref.id:
		return False

	oid = asset.ref.id
	while True:
		if asset.ref.order_number > slot:
			order = server.cache.orders[oid][slot]

			# Remove the order if it isn't a move order
			if order.subtype != server.MERGEFLEET_ORDER:
				print "Merge order    - Current order (%r) wasn't a Merge order!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Merge order    - Object already had correct MergeFleet order."
			break
		else:
			print "Merge order    - Issuing orders to merge with %r" % (target.ref,)
			# We need to issue a move order instead.
			OrderCreateAfter(oid, -1, server.MERGEFLEET_ORDER)
			break

	return True

def Order_Build(asset, task, slot):
	oid = asset.ref.id

	# Do a "probe" to work out the types
	OrderCreateAfter(oid, 0, server.BUILDFLEET_ORDER, [], [], 0, "")
	result = server.cache.orders[oid][0]
	OrderRemove(oid, 0)
	ships = {}
	for id, name, max in result.ships[0]:
		ships[name] = id

	# Add the new build order
	tobuild = []
	if task.type in (Task.COLONISE, Task.TAKEOVER):
		# If we are referencing a colonise, better build a frigate
		print "Issuing orders to build a frigate"
		tobuild.append((ships['Frigate'],1))

	if task.type in (Task.DESTROY, Task.TAKEOVER):
		# Better build a battleship
		print "Issuing orders to build a battleship"
		tobuild.append((ships['Battleship'],1))

	while True:
		if asset.ref.order_number > slot:
			order = server.cache.orders[oid][slot]

			# Remove the order if it isn't a colonise order
			if order.subtype != server.BUILDFLEET_ORDER:
				print "Build order    - Current order (%r) wasn't a build order!" % order
				OrderRemove(oid, slot)
				continue

			if order.ships[1] != tobuild:
				print "Build order    - Current order (%r) wasn't building the correct stuff!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Build order    - Already had correct build order."
			break
		else:
			print "Build order    - Issuing new order build."
			# We need to issue a move order instead.
			OrderCreateAfter(oid, 0, server.BUILDFLEET_ORDER, [], tobuild, 0, "A robot army!")
			break

	return True
