from inc_noesis import *
import os
import subprocess
from math import sqrt, sin, cos
# import rpdb
# debugger = rpdb.Rpdb()
# debugger.set_trace()

# =================================================================
# Plugin Options, a few of them are exposed as commands (see below)
# =================================================================

#misc
bLog = True				# Display log, with some progress info 

#cloth options
bComputeCloth = True	# Compute cloth data and physics' drivers + fix cloth meshes using the NUNO/NUNV sections
bDisplayCloth = True	# Discard cloth meshes or not, you may want to put it to false if cloth get in the way during animations since they won't move as they are supposed to be animated by the physics' engine at runtime
bDisplayDrivers = True	# Discard cloth drivers and physics' bones or not

#paired files options
bLoadG1T = True			# Allow to choose a paired .g1t file
bLoadG1MS = False			# Allow to choose a paired .g1m skeleton file. Only choose this option if the skeleton is in a separate g1m
bLoadG1MOid = False			# Allow to choose a paired Oid.bin skeleton bone names file.
bAutoLoadG1MS = True		# Load the first g1m in the same folder as skeleton
bLoadG1AG2A = False	 		# Allow to choose a paired .g1a/.g2a file
bLoadG1AG2AFolder = False	# Allow to choose a folder, all .g1a/.g2a files in this folder will be loaded
bLoadG1H = False				#Allow to choose a paired .g1h file
G1HOffset = 20				#Offset between different morph targets
# =================================================================
# Miscenalleous
# =================================================================

def Align(bs, n):
	value = bs.tell() % n
	if (value):
		bs.seek(n - value, 1)

def registerNoesisTypes():
	handle = noesis.register("Koei Tecmo KTGL Texture",".g1t")
	noesis.setHandlerTypeCheck(handle, CheckTextureType)
	noesis.setHandlerLoadRGBA(handle, LoadRGBA)	
	handle = noesis.register("Koei Tecmo KTGL Model", ".g1m")
	noesis.setHandlerTypeCheck(handle, CheckModelType)
	noesis.setHandlerLoadModel(handle, LoadModel)
	noesis.addOption(handle, "-g1mskeleton", "Override G1MS section from another file", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1mautoskeleton", "Override G1MS section from another file", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1mskeletonoid", "Read skeleton bone names from another file", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1mtexture", "Specify G1T path", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1manimations", "Load Specified Animations", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1manimationdir", "Load Specified Animations from directories", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1mmorph", "Load morph targets from file", noesis.OPTFLAG_WANTARG)
	noesis.addOption(handle, "-g1mcloth", "Compute Cloth Data", 0)
	noesis.addOption(handle, "-g1mdriver", "Compute Driver Data", 0)		
	if (bLog):
		noesis.logPopup()
	return 1

HEADER_ID1 = 0x47314d5f  
HEADER_ID2 = 0x5F4D3147  
HEADER_ID3 = 0x47543147 
HEADER_ID4 = 0x47315447

# =================================================================
# Noesis check type
# =================================================================

def CheckModelType(data):
	bs = NoeBitStream(data)
	if len(data) < 16:
		print("Invalid g1m file, too small")
		return 0
	bs.seek(0, NOESEEK_ABS)
	id = bs.readInt()
	if id not in [HEADER_ID1,HEADER_ID2]:
		print("Header not recognized")
		return 0
	return 1

def CheckTextureType(data):
	bs = NoeBitStream(data)
	if len(data) < 16:
		print("Invalid g1t file, too small")
		return 0
	bs.seek(0, NOESEEK_ABS)
	id = bs.readInt()
	if id not in [HEADER_ID3,HEADER_ID4]:
		print("Header not recognized")
		return 0
	return 1
	
def ValidateInputDirectory(inVal):
	if os.path.isdir(inVal) is not True:
		return "'" + inVal + "' is not a valid directory."
	return None
	
# =================================================================
# VertexSpecs and Spec classes, used to store all attributes and values
# =================================================================

class VertexSpecs:
	def __init__(self):
		self.bufferID = None
		self.offset = None
		self.attribute = None
		self.typeHandler = None
		self.layer = None


class Spec:
	def __init__(self):
		self.count = None
		self.list = []

# =================================================================


# Buffer class, used for vertex, index etc buffers
# =================================================================

class Buffer:
	def __init__(self):
		self.strideSize = None
		self.elementCount = None
		self.offset = None


# =================================================================
# Mesh, Material and LOD classes
# =================================================================

class Mesh:
	def __init__(self):
		self.numVerts = 0
		self.numIdx = 0
		self.stride = 0
		self.hasNoBoneIndice = False
		self.hasNoBoneWeight = False
		self.triangles = []
		self.vertPosBuff = []
		self.vertPosStride = None
		self.vertUVBuff = []
		self.vertUVStride = None
		self.vertNormBuff = []
		self.vertNormStride = None
		self.colorBuffer = []
		self.tangentBuffer = []
		self.skinWeightList = []
		self.skinIndiceList = []
		self.oldSkinIndiceList = []
		self.clothStuff1Buffer = []
		self.clothStuff2Buffer = []
		self.clothStuff3Buffer = []
		self.clothStuff4Buffer = []
		self.clothStuff5Buffer = []
		self.fogBuffer = []
		self.binormalBuffer = []
		self.weightTypeList = []
		self.indiceTypeList = []
		self.idxBuff = bytes()
		self.uvType = None
		self.uvOff = None
		self.normType = None
		self.normOff = None
		self.matList = []
		self.textureList = []
		self.vertCount = None


class Material:
	def __init__(self):
		self.IDStart = 0
		self.IDCount = 0
		self.idxType = None
		self.primType = None
		self.diffuse = 'default'
		self.normal = 'default'

class Texture:
	def __init__(self):
		self.id = 0
		self.layer = 0
		self.type = 0
		self.subtype = 0
		self.key = "UNKNOWN_0"

class LOD:
	def __init__(self):
		self.name = ""
		self.ID = 0
		self.ID2 = 0
		self.indices = []


class LODList:
	def __init__(self):
		self.count = None
		self.list = []

# =================================================================


# G1M Class, with all the containers for the model
# =================================================================

class G1M:
	def __init__(self):
		self.meshCount = None
		self.boneMapList = []
		self.boneMapListCloth = []
		self.meshList = []
		self.specList = []
		self.lodList = []
		self.vertBufferList = []
		self.indiceBufferList = []
		self.meshInfoList = []
		self.matList = []
		self.textureList = []

G1MGM_MATERIAL_KEYS = [None, "COLOR", "COMBINED_PBR_BGR", "NORMAL", None, "DIRT"]

# =================================================================
# G1M's chunks and sections parsers
# =================================================================

def processChunkType1(bs):
	# ??????
	return 1


def processChunkType2(bs):
	# Materials
	count = bs.readInt()
	for i in range(count):
		bs.read('i')  # Always 0 ?
		textureCount = bs.readUInt()
		bs.read('i')  # 0,1 or -1
		bs.read('i')  # 0, 1 or -1
		List = []
		for j in range(textureCount):
			texture = Texture()
			texture.id = bs.readUShort()
			texture.layer = bs.readUShort()
			texture.type = bs.readUShort()
			texture.subtype = bs.readUShort()
			bs.readUShort()
			bs.readUShort()
			List.append(texture)
			texture.key = G1MGM_MATERIAL_KEYS[texture.type] if texture.type < len(G1MGM_MATERIAL_KEYS) else None
			if texture.key == None:
				texture.key = "UNKNOWN_%X" % (texture.type)
			print("Found Texture Material Info: (%d, %d, %d, %d, %s)" % (texture.id, texture.layer, texture.type, texture.subtype, texture.key))
		g1m.textureList.append(List)


def processChunkType3(bs):
	# Shader section, we skip
	return 1


def processChunkType4(bs):
	# Vertex buffer
	count = bs.readInt()
	for j in range(count):
		buffer = Buffer()
		bs.readInt()
		buffer.strideSize = bs.readInt()
		buffer.elementCount = bs.readInt()
		bs.readInt()
		buffer.offset = bs.tell()
		g1m.vertBufferList.append(buffer)
		bs.seek(buffer.elementCount * buffer.strideSize, 1)


def processChunkType5(bs):
	# Specs
	count = bs.readInt()
	for i in range(count):
		countBis = bs.readInt()
		bufferList = [bs.readInt() for j in range(countBis)]
		spec = Spec()
		specCount = bs.readInt()
		spec.count = specCount
		for j in range(specCount):
			vertSpec = VertexSpecs()
			vertSpec.bufferID = bufferList[bs.readUShort()]
			vertSpec.offset = bs.readUShort()
			# vertSpec.typeHandler = bs.readUShort()
			b1 = bs.readUByte()
			b2 = bs.readUByte()			
			vertSpec.typeHandler = (b1 << 8) | b2
			vertSpec.attribute = bs.readUByte()
			vertSpec.layer = bs.readUByte()
			spec.list.append(vertSpec)
		g1m.specList.append(spec)


def processChunkType6(bs):
	# Joint map info
	count = bs.readInt()
	for i in range(count):
		List1 = []
		List2 = []
		countBis = bs.readInt()
		for j in range(countBis):
			bs.readUInt()
			clothIndex = bs.readUInt() & 0xFFFF
			jointIndex = bs.readUInt() & 0xFFFF
			# if clothIndex!=0:
			# print("cloth " + str(hex(clothIndex)))
			# bs.readUShort() # unknown, always 0 ?
			List1.append(jointIndex)
			List2.append(clothIndex)
		g1m.boneMapList.append(List1)
		g1m.boneMapListCloth.append(List2)


def processChunkType7(bs):
	# Index buffer
	count = bs.readUInt()
	for i in range(count):
		buffer = Buffer()
		buffer.elementCount = bs.readUInt()
		typeHandler = bs.readUInt()
		bs.readUInt()
		if typeHandler == 0x08:
			buffer.strideSize = 1
		elif typeHandler == 0x10:
			buffer.strideSize = 2
		elif typeHandler == 0x20:
			buffer.strideSize = 4
		else:
			print("UNKNOWN INDEX SIZE")
		buffer.offset = bs.tell()
		bs.seek(buffer.elementCount * buffer.strideSize, 1)
		Align(bs, 4)
		g1m.indiceBufferList.append(buffer)


def processChunkType8(bs):
	# Submeshes' info
	count = bs.readUInt()
	for i in range(count):
		# CRITICAL check if the entry is valid
		g1m.meshInfoList.append([bs.readUInt() for j in range(14)])

	# Unknown             0x0000
	# VertexBufferID      0x0001
	# IndexIntoJointMap   0x0002
	# Unknown             0x0003
	# Unknown             0x0004
	# MaterialID          0x0005
	# TextureID           0x0006
	# IndexBufferID       0x0007
	# Unknown             0x0008
	# IndexBufferFormat   0x0009
	# VertexBufferOffset  0x000A
	# VertexBufferCount   0x000B
	# IndexBufferOffset   0x000C
	# IndexBufferCount    0x000D


def processChunkType9(bs):
	# LOD info
	count = bs.readUInt()
	for i in range(count):
		lodMeshContainer = LODList()
		bs.read('3i')
		meshCount1 = bs.readUInt()
		meshCount2 = bs.readUInt()
		bs.read('4i')
		lodMeshContainer.count = meshCount1 + meshCount2
		for j in range(meshCount1 + meshCount2):
			lod = LOD()
			lod.name = noeStrFromBytes(bs.readBytes(16))
			lod.ID = bs.readUInt()
			lod.ID2 = bs.readUInt()
			indexCount = bs.readUInt()
			for k in range(indexCount):
				a = bs.readUInt()
				lod.indices.append(a)
				if (debug):
					print(i, a)
			if (indexCount == 0):
				bs.readUInt()
			lodMeshContainer.list.append(lod)
		g1m.lodList.append(lodMeshContainer)


def parseG1MS(currentPosition, bs, isDefault = True):
	jointDataOffset = bs.readUInt()
	conditionNumber = bs.readUShort()
	if isDefault and conditionNumber == 0:
		print("Skeleton layering detected...");
		if g1sData is not None: # Skeleton Layer
			bs2 = NoeBitStream(g1sData)
			bs2.setEndian(endian)
			A = [bs2.readUInt() for j in range(6)]
			bs2.seek(A[3])
			for i in range(A[5]):
				currentPosition = bs2.tell()
				chunkName = bs2.readInt()
				chunkVersion = noeStrFromBytes(bs2.readBytes(4))
				chunkSize = bs2.readInt()
				if chunkName == 0x47314D53:
					return parseG1MS(currentPosition, bs2, False)
				bs2.seek(currentPosition + chunkSize)
	bs.readUShort()
	jointCount = bs.readUShort()
	jointIndicesCount = bs.readUShort()
	bs.read('I')
	if (debug):
		print("Skeleton with " + str(jointCount) + " bones and " + str(jointIndicesCount) + " indices")
	for i in range(jointIndicesCount):
		id = bs.readUShort()
		boneIDList.append(id)
		if (id != 0xFFFF):
			boneToBoneID[id] = i
	bs.seek(currentPosition + jointDataOffset)
	for i in range(jointCount):
		bs.read('3f')  # scale
		parentID = bs.readInt()
		quaternionRotation = [bs.readFloat() for j in range(4)]
		position = [bs.readFloat() for j in range(3)]
		bs.read('f')
		boneMatrixTransform = NoeQuat(quaternionRotation).toMat43().inverse()
		boneMatrixTransform[3] = NoeVec3(position)
		bone = NoeBone(i, 'bone_' + str(boneToBoneID[i]), boneMatrixTransform, None, parentID)
		boneList.append(bone)
	for bone in boneList:
		parentId = bone.parentIndex
		if parentId != -1:
			bone.setMatrix(bone.getMatrix() * boneList[parentId].getMatrix())
	print("Skeleton parsed")
	return 1

def parseG1MOid(bs):
	if len(boneList) == 0: 
		return 1
	stringList = []
	while(1):
		length = bs.readByte()
		if (length == 255 or length == -1):
			break
		string = noeStrFromBytes(bs.readBytes(length))
		stringList.append(string)

	if len(stringList) < 1:
		print("Oid is too small!")
		return 0

	if stringList[0] == "HeaderCharaOid":
		if len(stringList) < 4:
			print("Oid is too small!")
			return 0

		if stringList[2] != "1":
			print("Expected Oid constant is not 1! Might break!")

		for n, b in zip(stringList[3:], boneList):
			b.name = n.split(',')[-1]

		if boneList[0].name == "root":
			boneList[0].name = stringList[1].split(':')[-1]
	else:
		for n, b in zip(stringList, boneList):
			b.name = n

	print("Bone names %s parsed" % stringList[1])
	return 1

def parseG1MF(bs):
	Bytes = bs.read('30i')
	# CRITICAL CHECK IF THIS INFO IS CONSISTENT
	g1m.meshCount = Bytes[13]
	if (debug):
		print("Mesh Count = " + str(g1m.meshCount))

def parseG1MG(bs):
	platform = noeStrFromBytes(bs.readBytes(4))  # NX_ for Switch for example
	bs.readFloat()  # unknown
	# Bounding box info
	min_x = bs.readFloat()
	min_y = bs.readFloat()
	min_z = bs.readFloat()
	max_x = bs.readFloat()
	max_y = bs.readFloat()
	max_z = bs.readFloat()
	if (debug):
		print("Bounding box info :")
		print(min_x)
		print(min_y)
		print(min_z)
		print(max_x)
		print(max_y)
		print(max_z)

	count = bs.readInt()
	for j in range(count):
		currentPosition = bs.tell()
		chunkName = bs.readInt()
		chunkSize = bs.readInt()
		if (chunkName == 0x00010001):
			processChunkType1(bs)
		elif (chunkName == 0x00010002):
			processChunkType2(bs)
		elif (chunkName == 0x00010003):
			processChunkType3(bs)
		elif (chunkName == 0x00010004):
			processChunkType4(bs)
		elif (chunkName == 0x00010005):
			processChunkType5(bs)
		elif (chunkName == 0x00010006):
			processChunkType6(bs)
		elif (chunkName == 0x00010007):
			processChunkType7(bs)
		elif (chunkName == 0x00010008):
			processChunkType8(bs)
		elif (chunkName == 0x00010009):
			processChunkType9(bs)
		else:
			print("Error, unknown G1MG section")
			return 0
		bs.seek(currentPosition + chunkSize)


# =================================================================
# NUNO helper structs, parser and info
# =================================================================

# NUNO influence data structure
class NUNOInfluence:
	def __init__(self):
		self.P1 = None
		self.P2 = None
		self.P3 = None
		self.P4 = None
		self.P5 = None
		self.P6 = None


# NUNO 0302 type struct
class NUNOType0302Struct:
	def __init__(self):
		self.parentBoneID = None
		self.controlPoint = None


# NUNO 0303 type struct, used by 0501 version too
class NUNOType0303Struct:
	def __init__(self):
		self.parentBoneID = None
		self.controlPoints = []
		self.influences = []
		self.name = ""


def parseNUNOSection0301(chunkVersion, bs):
	nunotype0301 = NUNOType0303Struct()
	nunotype0301.name = "nuno"
	bs.read('i')
	controlPointCount = bs.readUInt()
	unknownSectionCount = bs.readUInt()
	unknown1 = bs.readInt()
	unknown2 = bs.readInt()
	unknown3 = bs.readInt()
	bs.read('2i')
	nunotype0301.parentBoneID = bs.readInt()

	bs.readBytes(0x40)
	if (chunkVersion >= 0x30303235):
		bs.readBytes(0x10)

	for i in range(controlPointCount):
		nunotype0301.controlPoints.append(NoeVec3([bs.readFloat() for j in range(3)]))
		bs.read('f')
	for i in range(controlPointCount):
		influence = NUNOInfluence()
		influence.P1 = bs.readInt()
		influence.P2 = bs.readInt()
		influence.P3 = bs.readInt()
		influence.P4 = bs.readInt()
		influence.P5 = bs.readFloat()
		influence.P6 = bs.readFloat()
		nunotype0301.influences.append(influence)

	bs.readBytes(48 * unknownSectionCount)
	bs.readBytes(4 * unknown1)
	bs.readBytes(4 * unknown2)
	bs.readBytes(4 * unknown3)

	NUNO0303StructList.append(nunotype0301)


# Weird section, not taken into account when constructing models, need more work
def parseNUNOSection0302(chunkVersion, bs):
	nunotype0302 = NUNOType0302Struct()
	nunotype0302.name = "nuno"
	nunotype0302.parentBoneID = bs.readInt()
	bs.readBytes(0x68)
	point = [bs.readFloat() for j in range(3)]
	nunotype0302.controlPoint = NoeVec3(point)
	bs.readBytes(0x08)
	NUNO0302StructList.append(nunotype0302)


def parseNUNOSection0303(chunkVersion, bs):
	nunotype0303 = NUNOType0303Struct()
	nunotype0303.name = "nuno"
	bs.read('i')
	controlPointCount = bs.readUInt()
	unknownSectionCount = bs.readUInt()
	unknown1 = bs.readInt()
	nunotype0303.parentBoneID = bs.readInt()
	unknown2 = bs.readInt()
	bs.readBytes(0xB0)
	if (chunkVersion >= 0x30303235):
		bs.readBytes(0x10)

	for i in range(controlPointCount):
		nunotype0303.controlPoints.append(NoeVec3([bs.readFloat() for j in range(3)]))
		bs.read('f')
	for i in range(controlPointCount):
		influence = NUNOInfluence()
		influence.P1 = bs.readInt()
		influence.P2 = bs.readInt()
		influence.P3 = bs.readInt()
		influence.P4 = bs.readInt()
		influence.P5 = bs.readFloat()
		influence.P6 = bs.readFloat()
		nunotype0303.influences.append(influence)

	# reading the unknown sections data
	bs.readBytes(48 * unknownSectionCount)
	bs.readBytes(4 * unknown1)
	bs.readBytes(8 * unknown2)

	NUNO0303StructList.append(nunotype0303)


def parseNUNO(chunkVersion, bs):
	# number of sections
	count = bs.readInt()
	for i in range(count):
		currentPosition = bs.tell()
		subChunkType = bs.readInt()
		subChunkSize = bs.readInt()
		subChunkCount = bs.readInt()
		for j in range(subChunkCount):
			if (subChunkType == 0x00030001):
				parseNUNOSection0301(chunkVersion, bs)
			elif (subChunkType == 0x00030002):
				parseNUNOSection0302(chunkVersion, bs)
			elif (subChunkType == 0x00030003):
				parseNUNOSection0303(chunkVersion, bs)
			elif (subChunkType == 0x00030004):
				continue
			else:
				print("Unsupported NUNOSubChunk, may lead to errors")
		bs.seek(currentPosition + subChunkSize)


# =================================================================
# NUNV helper structs, parser and info. Same kind of structs as NUNO
# =================================================================
def parseNUNVSection0501(chunkVersion, bs):
	nunvtype0501 = NUNOType0303Struct()  # same struct
	nunvtype0501.name = "nunv"
	bs.read('i')
	controlPointCount = bs.readUInt()
	unknownSectionCount = bs.readUInt()
	unknown1 = bs.readInt()
	nunvtype0501.parentBoneID = bs.readInt()
	bs.readBytes(0x50)
	if (chunkVersion >= 0x30303131):
		bs.readBytes(0x10)

	for i in range(controlPointCount):
		nunvtype0501.controlPoints.append(NoeVec3([bs.readFloat() for j in range(3)]))
		bs.read('f')
	for i in range(controlPointCount):
		influence = NUNOInfluence()
		influence.P1 = bs.readInt()
		influence.P2 = bs.readInt()
		influence.P3 = bs.readInt()
		influence.P4 = bs.readInt()
		influence.P5 = bs.readFloat()
		influence.P6 = bs.readFloat()
		nunvtype0501.influences.append(influence)

	# reading the unknown sections data
	bs.readBytes(48 * unknownSectionCount)
	bs.readBytes(4 * unknown1)

	NUNV0303StructList.append(nunvtype0501)


def parseNUNV(chunkVersion, bs):
	# number of sections
	count = bs.readInt()
	for i in range(count):
		currentPosition = bs.tell()
		subChunkType = bs.readInt()
		subChunkSize = bs.readInt()
		subChunkCount = bs.readInt()
		for j in range(subChunkCount):
			if (subChunkType == 0x00050001):
				parseNUNVSection0501(chunkVersion, bs)
			else:
				print("Unsupported NUNVSubChunk")
		bs.seek(currentPosition + subChunkSize)

# =================================================================
# The G1T parser, all info about textures is there
# =================================================================
def processG1T(bs):
	if bLog:
		noesis.logPopup()
	magic = bs.read('<i')[0]
	if (magic == 0x47543147):
		endiang1t = NOE_BIGENDIAN
	elif (magic == 0x47315447):
		endiang1t = NOE_LITTLEENDIAN
	bs.setEndian(endiang1t)
	version = noeStrFromBytes(bs.readBytes(4))
	filesize = bs.readInt()
	tableoffset = bs.readInt()
	textureCount = bs.readInt()
	platform = bs.readInt()
	bs.seek(tableoffset)
	offsetList = [bs.readUInt() for j in range(textureCount)]
	for i in range(textureCount):
		bs.seek(tableoffset + offsetList[i])
		mipSys = bs.readUByte()
		mipMapNumber = mipSys >> 4
		texSys = mipSys & 0xF
		textureFormat = bs.readUByte()
		dxdy = bs.readUByte()
		bs.readUByte()
		bs.readUByte()
		bs.readUByte()
		bs.readUByte()
		extra_header_version = bs.readUByte()
		height = pow(2, int(dxdy>> 4))
		width = pow(2, dxdy & 0x0F)
		headerSize = 0x8
		if extra_header_version > 0:
			extraDataSize = bs.readUInt()
			print("Extra Header found: Size %d, Version %d" % (extraDataSize, extra_header_version))
			if extraDataSize < 0xC or extraDataSize > 0x14:
				print("Extra Texture Data is not between 0xC and 0x14 Bytes! Might Die!")
			headerSize += extraDataSize
			bs.readUInt()
			bs.readUInt()
			if extraDataSize >= 0x10:
				width = bs.readUInt()
			if extraDataSize >= 0x14:
				height = bs.readUInt()
		computedSize = -1
		mortonWidth = 0
		bRaw = False
		if (textureFormat == 0x0):
			computedSize = width * height * 4
			bRaw = True
			format == "r8 g8 b8 a8"	
		elif (textureFormat == 0x1):
			bRaw = True
			format = noesis.NOESISTEX_RGBA32
		elif (textureFormat == 0x2):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x3):
			format = noesis.NOESISTEX_DXT5
		elif (textureFormat == 0x6):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x7):
			format = noesis.NOESISTEX_DXT3
		elif (textureFormat == 0x8):
			format = noesis.NOESISTEX_DXT5
		elif (textureFormat == 0xF):
			computedSize = width * height 
			bRaw = True
			format = "a8"			
		elif (textureFormat == 0x10):
			format = noesis.NOESISTEX_DXT1
			mortonWidth = 0x4
		elif (textureFormat == 0x12):
			format = noesis.NOESISTEX_DXT5
			mortonWidth = 0x8
		elif (textureFormat == 0x34):
			computedSize = width * height * 2
			bRaw = True
			format = "b5 g6 r5"
		elif (textureFormat == 0x36):
			computedSize = width * height * 2 
			bRaw = True
			format = "a4 b4 g4 r4"
		elif (textureFormat == 0x3C):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x3D):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x56):
			format = "ETC1"
			computedSize = width * height // 2
		elif (textureFormat == 0x59):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x5B):
			format = noesis.NOESISTEX_DXT5
		elif (textureFormat == 0x5C):
			format = noesis.FOURCC_ATI1
		elif (textureFormat == 0x5D):
			format = noesis.FOURCC_ATI2
		elif (textureFormat == 0x5E):
			format = noesis.FOURCC_BC6H
		elif (textureFormat == 0x5F):
			format = noesis.FOURCC_BC7
		elif (textureFormat == 0x60):
			format = noesis.NOESISTEX_DXT1
		elif (textureFormat == 0x62):
			format = noesis.NOESISTEX_DXT5
		elif (textureFormat == 0x6F):
			format = "ETC1"
			computedSize = width * height
			if i < len(offsetList) - 1:
				offsetList[i + 1] = offsetList[i] + headerSize + computedSize
		else:
			format = noesis.NOESISTEX_UNKNOWN
			print("possible unknown format !")
		textureName = str(i) + '.dds'
		if computedSize >= 0:
			textureData = bs.readBytes(computedSize)
		else:
			if i < textureCount - 1:			
				textureData = bs.readBytes(offsetList[i + 1] - offsetList[i] - headerSize)
				datasize = offsetList[i + 1] - offsetList[i] - headerSize
			else:
				textureData = bs.readBytes(bs.dataSize - offsetList[i] - headerSize - tableoffset)	
				datasize = bs.dataSize - offsetList[i] - headerSize - tableoffset
		print("Loaded Texture %d of %d; %dx%d; Format %X; Size %X; System %X" % (i + 1, textureCount, width, height, textureFormat, len(textureData), platform))
		if platform == 2:
			textureData = rapi.swapEndianArray(textureData, 2)
		if format == "ETC1":
			pvrTex = (b'\x50\x56\x52\x03\x02\x00\x00\x00')
			pvrTex += struct.pack("I", 0x6)            
			pvrTex += (b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')            
			pvrTex += struct.pack("I", width)
			pvrTex += struct.pack("I", height)
			pvrTex += (b'\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00')
			pvrTex += textureData	
			dstFilePath = noesis.getScenesPath() + "ktgl_etctex.pvr"
			workingdir = noesis.getScenesPath()
			newfile = open(dstFilePath, 'wb')
			newfile.write(pvrTex)
			newfile.close()
			subprocess.Popen([noesis.getScenesPath() + 'PVR2PNG.bat', dstFilePath]).wait()
			textureData = rapi.loadIntoByteArray(dstFilePath + ".png")
			texture = rapi.loadTexByHandler(textureData, ".png")
			texture.name = textureName
			textureList.append(texture)
			continue			
		if platform == 0x0B: #PS4
			if format == noesis.NOESISTEX_DXT1:
				imgFmt = b'\x30\x92'
			elif format == noesis.NOESISTEX_DXT5:
				imgFmt = b'\x50\x92'
			gnfSize = datasize + 0x30
			width = width-1 + 0xC000
			height = ((height - 1) >> 2) + 0x7000
			gnfHeader = b'\x47\x4E\x46\x20\x28\x00\x00\x00\x02\x01\x00\x00'
			gnfHeader += bytearray(noePack("I", gnfSize))      
			gnfHeader += b'\x00\x00\x00\x00\x01\x00'
			gnfHeader += imgFmt                                
			gnfHeader += bytearray(noePack("H", width))    
			gnfHeader += bytearray(noePack("H", height))    
			gnfHeader += b'\xAC\x0F\xD0\xA4\x01\xE0\x7F\x00\x00\x00\x00\x00\x00\00\x00\x00'
			gnfHeader += bytearray(noePack("I", datasize))     
			gnfHeader += textureData     
			tex = rapi.loadTexByHandler(gnfHeader, ".gnf")
			textureList.append(tex)
			continue
		if texSys == 0 and mortonWidth > 0: print("MipSys is %d, but morton width is defined as %d-- Morton maybe not necessary!" % (texSys, mortonWidth))
		if mortonWidth > 0:
			if platform == 2:
				if bRaw:
					textureData = rapi.imageUntile360Raw(textureData, width, height, mortonWidth)
				else:
					textureData = rapi.imageUntile360DXT(textureData, width, height, mortonWidth * 2)
			else:
				textureData = rapi.imageFromMortonOrder(textureData, width >> 1, height >> 2, mortonWidth)
		if bRaw:
			textureData = rapi.imageDecodeRaw(textureData, width, height, format)
			format = noesis.NOESISTEX_RGBA32
		else:
			textureData = rapi.imageDecodeDXT(textureData, width, height, format)
			format = noesis.NOESISTEX_RGBA32
		texture = NoeTexture(textureName, width, height, textureData, format)
		textureList.append(texture)
	print("G1T file parsed")
# =================================================================
# G1H Morph Targets 
# =================================================================

def processMorphG1MG(currentPosition, meshID, bs):
	vertBufferList = []
	specList = []
	platform = noeStrFromBytes(bs.readBytes(4))
	bs.read('7f')
	count1 = bs.readInt()
	for j in range(count1):
		currentPosition = bs.tell()
		chunkName = bs.readInt()
		chunkSize = bs.readInt()
		if (chunkName == 0x00010004):
			count2 = bs.readInt()
			for j in range(count2):
				buffer = Buffer()
				bs.readInt()
				buffer.strideSize = bs.readInt()
				buffer.elementCount = bs.readInt()
				bs.readInt()
				buffer.offset = bs.tell()
				vertBufferList.append(buffer)
				bs.seek(buffer.elementCount * buffer.strideSize, 1)
		elif (chunkName == 0x00010005):
			count3 = bs.readInt()
			for i in range(count3):
				countBis = bs.readInt()
				bufferList = [bs.readInt() for j in range(countBis)]
				spec = Spec()
				specCount = bs.readInt()
				spec.count = specCount
				for j in range(specCount):
					vertSpec = VertexSpecs()
					vertSpec.bufferID = bufferList[bs.readUShort()]
					vertSpec.offset = bs.readUShort()
					# vertSpec.typeHandler = bs.readUShort()
					b1 = bs.readUByte()
					b2 = bs.readUByte()			
					vertSpec.typeHandler = (b1 << 8) | b2
					vertSpec.attribute = bs.readUByte()
					vertSpec.layer = bs.readUByte()
					spec.list.append(vertSpec)
				specList.append(spec)
		bs.seek(currentPosition + chunkSize)
	info = g1m.meshInfoList[meshID]
	spec = specList[0]
	for m in range(spec.count):
			element = spec.list[m]
			# Vertex positions
			if element.attribute == 0x0000:
				buffer = vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				vertPosBuff = []
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						pos = [bs.readFloat() for j in range(3)]
						vertPosBuff.append(NoeVec3(pos))
					elif element.typeHandler in [0x0003,0x0300]:
						pos = [bs.readFloat() for j in range(3)]
						vertPosBuff.append(NoeVec3(pos))
					elif element.typeHandler in [0x000B,0x0B00]:
						pos = [bs.readHalfFloat() for i in range(3)]
						vertPosBuff.append(NoeVec3(pos))
					else:
						print("unknown position type handler... " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
				morphMap[meshID].append(vertPosBuff)
	
def processG1H(bs):
	magic = bs.read('<i')[0]
	if (magic == 0x5F483147):
		endiang1h = NOE_BIGENDIAN
	elif (magic == 0x4731485F):
		endiang1h = NOE_LITTLEENDIAN
	bs.setEndian(endiang1h)
	version = noeStrFromBytes(bs.readBytes(4))
	filesize = bs.readInt()
	tableoffsetG1HP = bs.readUShort()
	G1HPCount = bs.readUShort()
	bs.seek(tableoffsetG1HP)
	G1HPOffsets = [bs.readUInt() for i in range(G1HPCount)]
	for G1HPOffset in G1HPOffsets:
		bs.seek(G1HPOffset)
		bs.read('3i')
		tableOffsetMorphT = bs.readUShort()
		meshID = bs.readUShort()
		morphMap[meshID]=[]
		morphTCount = bs.readUShort()
		bs.seek(G1HPOffset + tableOffsetMorphT)
		morphTOffsets = [bs.readUInt() for i in range(morphTCount)]
		print("Found " + str(len(morphTOffsets)) + " shapekeys for mesh " + str(meshID))
		for morphToffset in morphTOffsets:
			bs.seek(G1HPOffset + morphToffset)
			A = [bs.readUInt() for j in range(6)]
			bs.seek(A[3] + G1HPOffset + morphToffset)
			for i in range(A[5]):
				currentPosition = bs.tell()
				chunkName = bs.readInt()
				chunkVersion = noeStrFromBytes(bs.readBytes(4))
				chunkSize = bs.readInt()
				if (chunkName == 0x47314D47):
					processMorphG1MG(currentPosition, meshID, bs)
					break
				bs.seek(currentPosition + chunkSize)

# =================================================================
# G2A Animation 
# =================================================================
def itof(input):
	bytes = struct.pack('<i', input)
	return struct.unpack('<f', bytes)[0]

def qtoi(input):
	bytes = struct.pack('<Q', (input & 0xFFFFFFFFFFFFFFFF))
	return struct.unpack('<i', bytes[:4])[0]

def function1(transform, currentTime, totalTime):
	result = [0, 0, 0]
	time_pc = currentTime / totalTime
	time_squared = time_pc * time_pc
	time_cubed = time_squared * time_pc

	row1 = transform[0x0]
	row2 = transform[0x1]
	row3 = transform[0x2]
	row4 = transform[0x3]

	component_x = itof(((row1 >> 0x25) & 0x7800000) + 0x32000000)
	component_y = itof(((row2 >> 0x25) & 0x7800000) + 0x32000000)
	component_z = itof(((row3 >> 0x25) & 0x7800000) + 0x32000000)
	component_w = itof(((row4 >> 0x25) & 0x7800000) + 0x32000000)

	result[0x0] = qtoi((row4 >> 28) & 0xFFFFF000) * component_w * time_cubed + \
				  qtoi((row1 >> 28) & 0xFFFFF000) * component_x + \
				  qtoi((row2 >> 28) & 0xFFFFF000) * component_y * time_pc + \
				  qtoi((row3 >> 28) & 0xFFFFF000) * component_z * time_squared
	result[0x1] = qtoi((row4 >> 8) & 0xFFFFF000) * component_w * time_cubed + \
				  qtoi((row1 >> 8) & 0xFFFFF000) * component_x + \
				  qtoi((row2 >> 8) & 0xFFFFF000) * component_y * time_pc + \
				  qtoi((row3 >> 8) & 0xFFFFF000) * component_z * time_squared
	result[0x2] = qtoi(row4 << 12) * component_w * time_cubed + \
				  qtoi(row1 << 12) * component_x + \
				  qtoi(row2 << 12) * component_y * time_pc + \
				  qtoi(row3 << 12) * component_z * time_squared
	return result

def function2(v):
	q = [0, 0, 0, 0]
	angle = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
	s = sin(angle * 0.5)
	c = cos(angle * 0.5)
	if (angle > 0.000011920929):
		q[0] = v[0] * (s / angle)
		q[1] = v[1] * (s / angle)
		q[2] = v[2] * (s / angle)
	else:
		q[0] = v[0] * 0.5
		q[1] = v[1] * 0.5
		q[2] = v[2] * 0.5
	q[3] = c
	return q

def processG2A(bs, animCount, animName):
	keyFramedBoneList = []
	magic = noeStrFromBytes(bs.readBytes(4))
	version = noeStrFromBytes(bs.readBytes(4))
	filesize = bs.readInt()
	framerate = bs.readFloat()
	animationLength = bs.readBits(18)
	boneInfoSectionSize = bs.readBits(14)
	timingSectionSize = bs.readInt()
	entryCount = bs.readInt()
	bIsNewVersion = False
	if (version == "0500"):
		reserved = bs.readInt()
		bIsNewVersion = True
	boneInfoCount = boneInfoSectionSize >> 2
	tempPos = bs.tell()
	lastId = 0
	globalOffset = 0
	for i in range(boneInfoCount):
		bs.seek(tempPos + i * 4)
		splineTypeCount = bs.readBits(4)
		boneID = bs.readBits(8 if bIsNewVersion else 10)
		boneTimingDataOffset = bs.readBits(20 if bIsNewVersion else 18)
		if boneID < lastId:
			globalOffset+=1
		lastId = boneID
		boneID += globalOffset * (256 if bIsNewVersion else 1024)
		boneTimingDataOffset -= globalOffset
		bs.seek(tempPos + boneInfoSectionSize + boneTimingDataOffset)
	
		rotNoeKeyFramedValues = []
		posNoeKeyFramedValues = []
		scaleNoeKeyFramedValues = []
		for j in range(splineTypeCount):
			opcode = bs.readUShort()
			keyFrameCount = bs.readUShort()
			firstDataIndex = bs.readInt()
			keyFrameTimings = [bs.readUShort() for j in range(keyFrameCount)]
			Align(bs, 4)
			checkpoint = bs.tell()
			bs.seek(tempPos + boneInfoSectionSize + timingSectionSize + firstDataIndex * 32)
			quantizedData = []
			for k in range(keyFrameCount):
				quantizedData.append([bs.readInt64() for j in range(4)])
			for k in range(keyFrameCount - 1):
				if (opcode == 0):
					keyframe1, keyframe2 = keyFrameTimings[k], keyFrameTimings[k + 1]
					for l in range(keyframe2 - keyframe1):
						temp1 = function1(quantizedData[k], l, keyframe2 - keyframe1)
						temp2 = function2(temp1)
						rotationKeyframedValue = NoeKeyFramedValue((keyFrameTimings[k] + l) / framerate,
																   NoeQuat(temp2).transpose())
						rotNoeKeyFramedValues.append(rotationKeyframedValue)
				elif (opcode == 1):
					keyframe1, keyframe2 = keyFrameTimings[k], keyFrameTimings[k + 1]
					for l in range(keyframe2 - keyframe1):
						temp1 = function1(quantizedData[k], l, keyframe2 - keyframe1)
						positionKeyFramedValue = NoeKeyFramedValue((keyFrameTimings[k] + l) / framerate, NoeVec3(temp1))
						posNoeKeyFramedValues.append(positionKeyFramedValue)
				elif (opcode == 2):
					keyframe1, keyframe2 = keyFrameTimings[k], keyFrameTimings[k + 1]
					for l in range(keyframe2 - keyframe1):
						temp1 = function1(quantizedData[k], l, keyframe2 - keyframe1)
						scaleKeyFramedValue = NoeKeyFramedValue((keyFrameTimings[k] + l) / framerate, NoeVec3(temp1))
						scaleNoeKeyFramedValues.append(scaleKeyFramedValue)
			bs.seek(checkpoint)
		if (boneID < len(boneIDList)):
			actionBone = NoeKeyFramedBone(boneIDList[boneID])
			if (len(rotNoeKeyFramedValues) > 0):
				actionBone.setRotation(rotNoeKeyFramedValues, noesis.NOEKF_ROTATION_QUATERNION_4)
			if (len(posNoeKeyFramedValues) > 0):
				actionBone.setTranslation(posNoeKeyFramedValues, noesis.NOEKF_TRANSLATION_VECTOR_3)
			if (len(scaleNoeKeyFramedValues) > 0):
				actionBone.setScale(scaleNoeKeyFramedValues, noesis.NOEKF_SCALE_VECTOR_3)
			keyFramedBoneList.append(actionBone)
		else:
			print("G2A Animation not compatible with the skeleton")
			return -1
	anim = NoeKeyFramedAnim(animName, boneList, keyFramedBoneList, framerate)
	animationList.append(anim)
	print("G2A Animation " + str(animCount + 1) + " loaded")
	return framerate

# =================================================================
# G1A Animation 
# =================================================================

def function3(chanValues, chanTimes, indexr, componentCount):
	temp = []
	for u in range(componentCount):
		temp += chanTimes[indexr + u]
	alltimes = sorted(list(set(temp)))
	alltimes = [0.0] + alltimes
	allvalues = [[] for b in range(componentCount)]
	for u in range(componentCount):
		for t in alltimes:
			chanIndex = len(chanValues[indexr + u]) - 1
			for index, t1 in enumerate(chanTimes[indexr + u]):
				if t < t1:
					chanIndex = index
					break
			a, b, c, d = chanValues[indexr + u][chanIndex]
			t1 = chanTimes[indexr + u][chanIndex]
			if (chanIndex == 0):
				t0 = 0.0
			else:
				t0 = chanTimes[indexr + u][chanIndex - 1]
			tratio = (t - t0) / (t1 - t0)
			value = a * (tratio ** 3) + b * (tratio ** 2) + c * tratio + d
			allvalues[u].append(value)
	return [allvalues, alltimes]

def processG1A(bs, animCount, animName):
	keyFramedBoneList = []
	magic = noeStrFromBytes(bs.readBytes(4))
	version = noeStrFromBytes(bs.readBytes(4))
	filesize = bs.readInt()
	animationType = bs.readUShort()  # not sure
	unk1 = bs.readUShort()
	duration = bs.readFloat()  # in seconds
	QuantizedDataSectionOffset = bs.readUInt() * 0x10
	bs.read('6I')  # probably reserved
	tempPos1 = bs.tell()
	boneInfoCount = bs.readUShort()
	boneMaxID = bs.readUShort()

	tempPos2 = bs.tell()
	for i in range(boneInfoCount):
		bs.seek(tempPos2 + i * 8)
		boneID = bs.readUInt()
		splineInfoOffset = bs.readUInt()
		bs.seek(tempPos1 + splineInfoOffset * 0x10)

		tempPos3 = bs.tell()
		opcode = bs.readUInt()
		chanValues = []
		chanTimes = []
		componentCount = -1

		indexs = -1
		indexr = -1
		indexl = -1
		if (opcode == 0x1):
			componentCount = 2
		elif (opcode == 0x2):
			componentCount = 4
			indexr = 0
		elif (opcode == 0x4):
			componentCount = 7
			indexr = 0
			indexl = 4
		elif (opcode == 0x6):
			componentCount = 10
			indexs = 0
			indexr = 3
			indexl = 7
		elif (opcode == 0x8):
			componentCount = 7
			indexs = 0
			indexr = 3
		else:
			print("Unknown g1a opcode " + str(hex(opcode)) + " for bone index " + str(i))
		values = [[] for l in range(componentCount)]
		rotNoeKeyFramedValues = []
		posNoeKeyFramedValues = []
		scaleNoeKeyFramedValues = []
		for j in range(componentCount):
			bs.seek(tempPos3 + 4 + j * 8)
			keyFrameCount = bs.readUInt()
			quantizedDataOffset = bs.readUInt()
			bs.seek(tempPos3 + quantizedDataOffset * 0x10)
			quantizedData = []
			times = []
			for k in range(keyFrameCount):
				quantizedData.append([bs.readFloat() for l in range(4)])
			for k in range(keyFrameCount):
				times.append(bs.readFloat())
			chanValues.append(quantizedData)
			chanTimes.append(times)
		if (indexr >= 0):
			allvalues, alltimes = function3(chanValues, chanTimes, indexr, 4)
			for p in range(len(alltimes)):
				rotationKeyframedValue = NoeKeyFramedValue(alltimes[p], NoeQuat(
					[allvalues[0][p], allvalues[1][p], allvalues[2][p], allvalues[3][p]]).transpose())
				rotNoeKeyFramedValues.append(rotationKeyframedValue)
		if (indexl >= 0):
			allvalues, alltimes = function3(chanValues, chanTimes, indexl, 3)
			for p in range(len(alltimes)):
				positionKeyframedValue = NoeKeyFramedValue(alltimes[p],
														   NoeVec3([allvalues[0][p], allvalues[1][p], allvalues[2][p]]))
				posNoeKeyFramedValues.append(positionKeyframedValue)
		if (indexs >= 0):
			allvalues, alltimes = function3(chanValues, chanTimes, indexs, 3)
			for p in range(len(alltimes)):
				scaleKeyframedValue = NoeKeyFramedValue(alltimes[p],
														NoeVec3([allvalues[0][p], allvalues[+1][p], allvalues[2][p]]))
				scaleNoeKeyFramedValues.append(scaleKeyframedValue)

		if (boneID < len(boneIDList)):
			actionBone = NoeKeyFramedBone(boneIDList[boneID])
			if (len(rotNoeKeyFramedValues) > 0):
				actionBone.setRotation(rotNoeKeyFramedValues, noesis.NOEKF_ROTATION_QUATERNION_4)
			if (len(posNoeKeyFramedValues) > 0):
				actionBone.setTranslation(posNoeKeyFramedValues, noesis.NOEKF_TRANSLATION_VECTOR_3)
			if (len(scaleNoeKeyFramedValues) > 0):
				actionBone.setScale(scaleNoeKeyFramedValues, noesis.NOEKF_SCALE_VECTOR_3)
			keyFramedBoneList.append(actionBone)
		else:
			print("G1A Animation not compatible with the skeleton")
			return -1
	anim = NoeKeyFramedAnim(animName, boneList, keyFramedBoneList, 30)
	animationList.append(anim)
	print("G1A Animation " + str(animCount + 1) + " loaded")
	return 30

# =================================================================
# Function used when transforming cloth type 1 vertices
# =================================================================

def processClothVertex(position, weights, bones, nunoMap):
	temp = NoeVec3()
	temp += boneList[nunoMap[int(bones[0])]].getMatrix().transformPoint(position) * weights[0]
	temp += boneList[nunoMap[int(bones[1])]].getMatrix().transformPoint(position) * weights[1]
	temp += boneList[nunoMap[int(bones[2])]].getMatrix().transformPoint(position) * weights[2]
	temp += boneList[nunoMap[int(bones[3])]].getMatrix().transformPoint(position) * weights[3]
	return temp

# =================================================================
# Noesis load texture
# =================================================================

def LoadRGBA(data, texList):
	global textureList
	textureList = []
	g1tBs = NoeBitStream(data)
	processG1T(g1tBs)
	for tex in textureList:
		texList.append(tex)
	return 1

# =================================================================
# Noesis load model
# =================================================================

def LoadModel(data, mdlList):
	global g1m
	global g1sData
	global g1hData
	global textureList
	global boneList
	global boneIDList
	global boneToBoneID
	global animationList
	global driverMeshList
	global NUNO0302StructList
	global NUNO0303StructList
	global NUNV0303StructList
	global debug
	global globalFramerate
	global submeshesCount
	global currentMesh
	global KeepDrawing
	global endian
	global morphMap
	global G1MGM_MATERIAL_KEYS
	debug = False
	g1tData = None
	g1sData = None
	oidData = None
	g2aData = None
	g1hData = None
	animDir = None
	globalFramerate = None
	textureList = []
	boneList = []
	boneIDList = []
	boneToBoneID = {}
	morphMap = {}
	animationList = []
	animPaths = []
	NUNO0302StructList = []
	NUNO0303StructList = []
	NUNV0303StructList = []

	ctx = rapi.rpgCreateContext()
	bs = NoeBitStream(data)
	firstByte = bs.readByte()
	endian = 0
	if firstByte == 0x47:
		bs.setEndian(NOE_BIGENDIAN)
		rapi.rpgSetOption(noesis.RPGOPT_BIGENDIAN, 1)
		endian = NOE_BIGENDIAN
	else:
		bs.setEndian(NOE_LITTLEENDIAN)
		rapi.rpgSetOption(noesis.RPGOPT_BIGENDIAN, 0)
		endian = NOE_LITTLEENDIAN
	bs.seek(0)
	# For some reason KT sometimes stores copies of the exact same skeleton (FETH for ex), we only want to keep one of them
	hasNotParsedg1ms = True

	if bLoadG1T or noesis.optWasInvoked("-g1mtexture"):
		if (noesis.optWasInvoked("-g1mtexture")):
			with open(noesis.optGetArg("-g1mtexture")) as g1tStream:
				g1tData = g1tStream.read()
		else:
			g1tData = rapi.loadPairedFileOptional("texture file", ".g1t")
	if g1tData is not None:
		g1tDataBs = NoeBitStream(g1tData)
		g1tDataBs.setEndian(endian)
		processG1T(g1tDataBs)	
	
	if bAutoLoadG1MS or noesis.optWasInvoked("-g1mautoskeleton"):
		thisName = rapi.getInputName()
		dir = os.path.dirname(thisName)

		if thisName.endswith("_default.g1m") and rapi.checkFileExists(thisName[0:-12] + ".g1m"):
			g1sData = rapi.loadIntoByteArray(thisName[0:-12] + ".g1m")
			print("Skeleton detected at ", thisName[0:-12] + ".g1m")
		else:
			for root, dirs, files in os.walk(dir):
				for fileName in files:
					lowerName = fileName.lower()
					if lowerName.endswith(".g1m"):
						g1mPath = os.path.join(root, fileName)
						if (rapi.checkFileExists(g1mPath)):
							g1sData = rapi.loadIntoByteArray(g1mPath)
							print("Skeleton detected at ", g1mPath)
							break
				break
	
	if bLoadG1MS or noesis.optWasInvoked("-g1mskeleton"):
		if g1sData is None:
			if (noesis.optWasInvoked("-g1mskeleton")):
				with open(noesis.optGetArg("-g1mskeleton")) as g1sStream:
					g1sData = g1sStream.read()
			else:
				g1sData = rapi.loadPairedFileOptional("skeleton file", ".g1m")
	
	if bLoadG1MOid or noesis.optWasInvoked("-g1mskeletonoid"):
		if (noesis.optWasInvoked("-g1mskeletonoid")):
			with open(noesis.optGetArg("-g1mskeletonoid")) as oidStream:
				oidData = oidStream.read()
		else:
			oidData = rapi.loadPairedFileOptional("skeleton name file", "Oid.bin")

	if oidData is not None:
		bs3 = NoeBitStream(oidData)
		parseG1MOid(bs3)


	magic = noeStrFromBytes(bs.readBytes(4))
	version = noeStrFromBytes(bs.readBytes(4))
	filesize = bs.readUInt()
	firstChunkOffset = bs.readUInt()
	bs.read('I')  # Always 0 ?
	chunkCount = bs.readUInt()

	bs.seek(firstChunkOffset)
	g1m = G1M()

	if (debug):
		print("g1m file : " + str(magic) + str(version) + " with " + str(chunkCount) + " chunks.")

	supportedChunkNames = ["SM1G", "GM1G", "FM1G", "MM1G", "ONUN", "VNUN"]

	for i in range(chunkCount):
		currentPosition = bs.tell()
		chunkName = bs.readInt()
		chunkVersion = bs.readInt()  # version
		chunkSize = bs.readInt()

		if (chunkName not in supportedChunkNames and debug):
			print(chunkName + " unknown section !")
		if (debug):
			print(chunkName)
		if chunkName == 0x47314D53 and hasNotParsedg1ms:
			parseG1MS(currentPosition, bs)
			hasNotParsedg1ms = False
		elif chunkName == 0x47314D47:
			parseG1MG(bs)
		elif chunkName == 0x47314D46:
			parseG1MF(bs)
		elif chunkName == 0x4E554E4F:
			parseNUNO(chunkVersion, bs)
		elif chunkName == 0x4E554E56:
			parseNUNV(chunkVersion, bs)
		# elif chunkName==0x47314D4D:
		# parseG1MM(bs)
		bs.seek(currentPosition + chunkSize)	
	
	if bLoadG1AG2AFolder or noesis.optWasInvoked("-g1manimationdir"):
		if noesis.optWasInvoked("-g1manimationdir"):
			animDir = noesis.optGetArg("-g1manimationdir")
		else:
			animDir = noesis.userPrompt(noesis.NOEUSERVAL_FOLDERPATH, "Open Folder", "Select the folder to get the animations from", noesis.getSelectedDirectory(), ValidateInputDirectory)

		if animDir is not None:
			for root, dirs, files in os.walk(animDir):
				for fileName in files:
					lowerName = fileName.lower()
					if lowerName.endswith(".g1a") or lowerName.endswith(".g2a"):
						fullPath = os.path.join(root, fileName)
						animPaths.append(fullPath)	
	
	if bLoadG1AG2A or noesis.optWasInvoked("-g1manimations") or animDir is not None:
		animCount = 0		
		if animDir is None:
			if noesis.optWasInvoked("-g1manimations"):
				animPaths = noesis.optGetArg("-g1manimations").split(';')
			else:
				animLoop = True
				while (animLoop == True):
					animPath = rapi.loadPairedFileGetPath("animation file", ".g1a;*.g2a")
					if animPath is not None:
						animPaths.append(animPath[1])
					else:
						animLoop = False

		for animPath in animPaths:
			with open(animPath, "rb") as gaStream:
				animName = os.path.basename(animPath)[:-4] # Filename without extension
				gaData = gaStream.read()
				gaBs = NoeBitStream(gaData)
				gaBs.setEndian(endian)
				magic = gaBs.readInt()
				gaBs.seek(0)
				tempFrame = -1
				if magic == 0x4732415F:
					tempframe = processG2A(gaBs, animCount, animName)
				elif magic == 0x4731415F:
					tempframe = processG1A(gaBs, animCount, animName)
				if tempframe != -1:
					globalFramerate = tempframe
					animCount += 1

	meshList = []
	matList = []
	driverMeshList = []
	
	
	for meshID in range(len(g1m.meshInfoList)):
		mesh = Mesh()
		meshList.append(mesh)
	
	if bLoadG1H or noesis.optWasInvoked("-g1mmorph"):
		if (noesis.optWasInvoked("-g1mmorph")):
			with open(noesis.optGetArg("-g1mmorph")) as g1morphStream:
				g1hData = g1morphStream.read()
		else:
			g1hData = rapi.loadPairedFileOptional("morph target file", ".g1h")		
	if g1hData is not None:
		g1hDataBs = NoeBitStream(g1hData)
		g1hDataBs.setEndian(endian)
		processG1H(g1hDataBs)
		
	# =================================================================
	# NUN bones and drivers meshes
	# =================================================================
	if (bComputeCloth or noesis.optWasInvoked("-g1mcloth")):
		NUNProps = []
		nunoOffset = 0
		clothMap = []
		if (len(NUNO0303StructList) != 0):
			nunoOffset = len(NUNO0303StructList)
		if (len(NUNO0303StructList) != 0):
			for nuno0303 in NUNO0303StructList:
				NUNProps.append(nuno0303)
		if (len(NUNV0303StructList) != 0):
			for nunv0303 in NUNV0303StructList:
				NUNProps.append(nunv0303)
		for prop in NUNProps:
			boneStart = len(boneList)
			parentBone = g1m.boneMapList[prop.parentBoneID - 1][0]
			nunoMap = {}
			driverMesh = Mesh()
			driverMesh.vertCount = 0
			for pointIndex in range(len(prop.controlPoints)):
				p = prop.controlPoints[pointIndex]
				link = prop.influences[pointIndex]
				nunoMap[pointIndex] = len(boneList)
				boneMatrixTransform = NoeQuat().toMat43().inverse()
				parentID = link.P3

				if (parentID == -1):
					parentID = parentBone
					boneMatrixTransform[3] = p
				else:
					parentID += boneStart
					boneMatrixTransform = boneList[parentBone].getMatrix() * boneList[parentID].getMatrix().inverse()
					p = boneMatrixTransform.transformPoint(p)
					boneMatrixTransform[3] = p
				bone = NoeBone(len(boneList), prop.name + 'bone_p'+str(parentBone) +"_" + str(len(boneList)), boneMatrixTransform, None,
							   parentID)
				bone.setMatrix(bone.getMatrix() * boneList[parentID].getMatrix())
				boneList.append(bone)

				boneMatrixUpdateTransform = boneList[len(boneList) - 1].getMatrix()
				updatedPosition = boneMatrixUpdateTransform.transformPoint(NoeVec3())
				driverMesh.vertPosBuff.append(updatedPosition)
				driverMesh.vertCount += 1
				driverMesh.skinWeightList.append(NoeVec4([1.0, 0.0, 0.0, 0.0]))
				driverMesh.skinIndiceList.append(NoeVec4([len(boneList) - 1, 0.0, 0.0, 0.0]))

				if (link.P1 > 0 and link.P3 > 0):
					driverMesh.triangles.append(NoeVec3([int(pointIndex), int(link.P1), int(link.P3)]))
				if (link.P2 > 0 and link.P4 > 0):
					driverMesh.triangles.append(NoeVec3([int(pointIndex), int(link.P2), int(link.P4)]))
			clothMap.append(nunoMap)
			driverMeshList.append(driverMesh)
	# =================================================================
	# Semantics and submeshes
	# =================================================================

	print("Mesh info parsing, may take a few seconds for some games")
	for infoID in range(len(g1m.meshInfoList)):
		info = g1m.meshInfoList[infoID]
		spec = g1m.specList[info[1]]
		mesh = meshList[info[1]]
		mat = Material()
		diffID = -1
		normID = -1
		if info[6] < len(g1m.textureList):
			for textureInfo in g1m.textureList[info[6]]:
				if textureInfo.key == "COLOR" and textureInfo.layer == 0 and diffID == -1:
					diffID = textureInfo.id
				if textureInfo.key == "NORMAL" and normID == -1:
					normID = textureInfo.id
		if diffID > -1:
			if diffID < len(textureList):
				mat.diffuse = textureList[diffID].name
			else:
				imgPath = os.path.dirname(rapi.getInputName()) + os.sep + str(diffID) + '.dds'
				if os.path.exists(imgPath) == True:
					mat.diffuse = imgPath
		if normID > -1:
			if normID < len(textureList):
				mat.normal = textureList[normID].name
			else:
				imgPath = os.path.dirname(rapi.getInputName()) + os.sep + str(normID) + '.dds'
				if os.path.exists(imgPath) == True:
					mat.normal = imgPath
		for m in range(spec.count):
			element = spec.list[m]
			# Vertex positions
			if element.attribute == 0x0000:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				clothStuff3Data = bytes()
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						pos = [bs.readFloat() for j in range(3)]
						mesh.vertPosBuff.append(NoeVec3(pos))
						clothStuff3 = bs.readFloat()
						mesh.clothStuff3Buffer.append(clothStuff3)
					elif element.typeHandler in [0x0003,0x0300]:
						pos = [bs.readFloat() for j in range(3)]
						mesh.vertPosBuff.append(NoeVec3(pos))
						clothStuff3 = bs.readFloat()
						mesh.clothStuff3Buffer.append(clothStuff3)
					elif element.typeHandler in [0x000B,0x0B00]:
						pos = [bs.readHalfFloat() for i in range(3)]
						mesh.vertPosBuff.append(NoeVec3(pos))
						clothStuff3 = bs.readHalfFloat()
						mesh.clothStuff3Buffer.append(clothStuff3)
					else:
						print("unknown position type handler... " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
				mesh.vertCount = buffer.elementCount
			# Normals
			if element.attribute in [0x0003,0x0300]:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						norm = [bs.readFloat() for j in range(3)]
						mesh.vertNormBuff.append(NoeVec3(norm))
						clothStuff4 = bs.readFloat()
						mesh.clothStuff4Buffer.append(clothStuff4)
					elif element.typeHandler in [0x0003,0x0300]:
						norm = [bs.readFloat() for j in range(3)]
						mesh.vertNormBuff.append(NoeVec3(norm))
						clothStuff4 = bs.readFloat()
						mesh.clothStuff4Buffer.append(clothStuff4)
					elif element.typeHandler in [0x000B,0x0B00]:
						norm = [bs.readHalfFloat() for i in range(3)]
						mesh.vertNormBuff.append(NoeVec3(norm))
						clothStuff4 = bs.readHalfFloat()
						mesh.clothStuff4Buffer.append(clothStuff4)
					else:
						print("unknown normal type handler... " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
			# UV1
			if element.attribute in [0x0005,0x0500]:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0001,0x0100]:
						if element.layer == 0:
							uv = [bs.readFloat() for i in range(2)]
							# uv=[bs.readHalfFloat() for i in range(2)]
							mesh.vertUVBuff.append(uv)
					elif element.typeHandler in [0x000A,0x0A00]:
						if element.layer == 0:
							uv = [bs.readHalfFloat() for i in range(2)]
							mesh.vertUVBuff.append(uv)
					elif element.typeHandler in [0x0003,0x0300]:
						clothStuff2 = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.clothStuff2Buffer.append(clothStuff2)
					elif element.typeHandler in [0x0005,0x0500]:
						clothStuff2 = NoeVec4([bs.readUByte() for i in range(4)])
						mesh.clothStuff2Buffer.append(clothStuff2)
					elif element.typeHandler in [0x0007,0x0700]:
						clothStuff2 = NoeVec4([bs.readHalfFloat() for i in range(4)])
						mesh.clothStuff2Buffer.append(clothStuff2)
					else:
						print("unknown uv type handler..." + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
			# Tangents
			if element.attribute in [0x0006,0x0600]:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						tangent = NoeVec4([bs.readFloat(), bs.readFloat(), bs.readFloat(), 1])
						mesh.tangentBuffer.append(tangent)
					elif element.typeHandler in [0x0003,0x0300]:
						tangent = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.tangentBuffer.append(tangent)
					elif element.typeHandler in [0x000B,0x0B00]:
						tangent = NoeVec4([bs.readHalfFloat() for i in range(4)])
						mesh.tangentBuffer.append(tangent)
					else:
						print("unknown tangent type handler " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
			# Binormals
			if element.attribute in [0x0007,0x0700]:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						binormal = NoeVec4([bs.readFloat(), bs.readFloat(), bs.readFloat(), 1])
						mesh.binormalBuffer.append(binormal)
					elif element.typeHandler in [0x0003,0x0300]:
						binormal = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.binormalBuffer.append(binormal)
					elif element.typeHandler in [0x000B,0x0B00]:
						binormal = NoeVec4([bs.readHalfFloat() for i in range(4)])
						mesh.binormalBuffer.append(binormal)
					else:
						print("unknown binormal type handler " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
			# Fog
			if element.attribute in [0x000B,0x0B00]:
				if element.layer == 0:  # layer 0
					buffer = g1m.vertBufferList[element.bufferID]
					bs.seek(buffer.offset + info[10] * buffer.strideSize)
					for n in range(info[11]):
						currentPos = bs.tell()
						bs.seek(currentPos + element.offset)
						if element.typeHandler in [0x0003,0x0300]:
							fog = NoeVec4([bs.readFloat() for i in range(4)])
							mesh.fogBuffer.append(fog)
						elif element.typeHandler in [0x0005,0x0500]:
							fog = NoeVec4([bs.readUByte() for i in range(4)])
							mesh.fogBuffer.append(fog)
						elif element.typeHandler in [0x0007,0x0700]:
							fog = NoeVec4([bs.readHalfFloat() for i in range(4)])
							mesh.fogBuffer.append(fog)
						elif element.typeHandler in [0x0009,0x0900]:
							fog = NoeVec4([bs.readFloat() for i in range(4)])
							mesh.fogBuffer.append(fog)
						elif element.typeHandler in [0x000D,0x0D00]:
							fog = NoeVec4([bs.readUByte() / 255 for i in range(4)])
							mesh.fogBuffer.append(fog)
						else:
							print("unknown fog type handler " + str(element.typeHandler))
						if (n != info[11] - 1):
							bs.seek(currentPos + buffer.strideSize)
			# Color
			if element.attribute in [0x000A,0x0A00]:
				if element.layer != 0:  # only interested in cloth stuff
					buffer = g1m.vertBufferList[element.bufferID]
					bs.seek(buffer.offset + info[10] * buffer.strideSize)
					for n in range(info[11]):
						currentPos = bs.tell()
						bs.seek(currentPos + element.offset)
						if element.typeHandler in [0x0002,0x0200]:
							clothStuff5 = NoeVec4([bs.readFloat(), bs.readFloat(), bs.readFloat(), 1])
							mesh.clothStuff5Buffer.append(clothStuff5)
						elif element.typeHandler in [0x0003,0x0300]:
							clothStuff5 = NoeVec4([bs.readFloat() for i in range(4)])
							mesh.clothStuff5Buffer.append(clothStuff5)
						elif element.typeHandler in [0x000B,0x0B00]:
							clothStuff5 = NoeVec4([bs.readHalfFloat() for i in range(4)])
							mesh.clothStuff5Buffer.append(clothStuff5)
						elif element.typeHandler in [0x000D,0x0D00]:
							clothStuff5 = NoeVec4([bs.readUByte() / 255 for i in range(4)])
							mesh.clothStuff5Buffer.append(clothStuff5)
						else:
							print("unknown clothstuff5 type handler " + str(element.typeHandler))
						if (n != info[11] - 1):
							bs.seek(currentPos + buffer.strideSize)
				elif element.layer == 0:
					buffer = g1m.vertBufferList[element.bufferID]
					bs.seek(buffer.offset + info[10] * buffer.strideSize)
					for n in range(info[11]):
						currentPos = bs.tell()
						bs.seek(currentPos + element.offset)
						if element.typeHandler in [0x0002,0x0200]:
							color = NoeVec4([bs.readFloat(), bs.readFloat(), bs.readFloat(), 1])
							mesh.colorBuffer.append(color)
						elif element.typeHandler in [0x0003,0x0300]:
							color = NoeVec4([bs.readFloat() for i in range(4)])
							mesh.colorBuffer.append(color)
						elif element.typeHandler in [0x000B,0x0B00]:
							color = NoeVec4([bs.readHalfFloat() for i in range(4)])
							mesh.colorBuffer.append(color)
						elif element.typeHandler in [0x000D,0x0D00]:
							color = NoeVec4([bs.readUByte() / 255 for i in range(4)])
							mesh.colorBuffer.append(color)
						else:
							print("unknown color type handler " + str(element.typeHandler))
						if (n != info[11] - 1):
							bs.seek(currentPos + buffer.strideSize)
			# PSize
			if element.attribute in [0x0004,0x0400]:
				buffer = g1m.vertBufferList[element.bufferID]
				bs.seek(buffer.offset + info[10] * buffer.strideSize)
				for n in range(info[11]):
					currentPos = bs.tell()
					bs.seek(currentPos + element.offset)
					if element.typeHandler in [0x0002,0x0200]:
						clothStuff1 = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.clothStuff1Buffer.append(clothStuff1)
					elif element.typeHandler in [0x0003,0x0300]:
						clothStuff1 = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.clothStuff1Buffer.append(clothStuff1)
					elif element.typeHandler in [0x0005,0x0500]:
						clothStuff1 = NoeVec4([bs.readUByte() for i in range(4)])
						mesh.clothStuff1Buffer.append(clothStuff1)
					elif element.typeHandler in [0x0007,0x0700]:
						clothStuff1 = NoeVec4([bs.readHalfFloat() for i in range(4)])
						mesh.clothStuff1Buffer.append(clothStuff1)
					elif element.typeHandler in [0x0009,0x0900]:
						clothStuff1 = NoeVec4([bs.readFloat() for i in range(4)])
						mesh.clothStuff1Buffer.append(clothStuff1)
					else:
						print("unknown psize type handler " + str(element.typeHandler))
					if (n != info[11] - 1):
						bs.seek(currentPos + buffer.strideSize)
			# Weights
			if element.attribute in [0x0001,0x0100]:
				# if element.layer==0:#layer 0
				if (True):
					buffer = g1m.vertBufferList[element.bufferID]
					bs.seek(buffer.offset + info[10] * buffer.strideSize)
					for n in range(info[11]):
						currentPos = bs.tell()
						bs.seek(currentPos + element.offset)
						if element.typeHandler == 0x0000:
							weight = NoeVec4([bs.readFloat(), 0, 0, 0])
							weight[1] = 1 - weight[0]
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x0001,0x0100]:
							weight = NoeVec4([bs.readFloat(), bs.readFloat(), 0, 0])
							weight[2] = 1 - weight[0] - weight[1]
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x0002,0x0200]:
							weight = NoeVec4([bs.readFloat(), bs.readFloat(), bs.readFloat(), 0])
							weight[3] = 1 - weight[0] - weight[1] - weight[2]
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x0003,0x0300]:
							weight = NoeVec4([bs.readFloat() for i in range(4)])
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x000A,0x0A00]:
							weight = NoeVec4([bs.readHalfFloat(), bs.readHalfFloat(), 0, 0])
							weight[2] = 1 - weight[0] - weight[1]
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x000B,0x0B00]:
							weight = NoeVec4([bs.readHalfFloat() for i in range(4)])
							mesh.skinWeightList.append(weight)
						elif element.typeHandler in [0x000D,0x0D00]:
							weight = NoeVec4([bs.readUByte() / 255 for i in range(4)])
							mesh.skinWeightList.append(weight)
						else:
							print("unknown weight type handler... " + str(element.typeHandler))
						if (n != info[11] - 1):
							bs.seek(currentPos + buffer.strideSize)

			# Bone Indices
			if element.attribute in [0x0002,0x0200]:
				# if element.layer == 0:
				if(True):
					buffer = g1m.vertBufferList[element.bufferID]
					bs.seek(buffer.offset + info[10] * buffer.strideSize)
					for n in range(info[11]):
						currentPos = bs.tell()
						bs.seek(currentPos + element.offset)
						if element.typeHandler in [0x0005,0x0500]:
							index = NoeVec4()
							index2 = NoeVec4()
							for a in range(4):
								ID = bs.readUByte()
								index2[a] = ID
								ID = ID // 3
								if len(g1m.boneMapList[info[2]]) > ID:
									ID = g1m.boneMapList[info[2]][ID]
								index[a] = ID
							mesh.skinIndiceList.append(index)
							mesh.oldSkinIndiceList.append(index2)
						elif element.typeHandler in [0x0007,0x0700]:
							index = NoeVec4()
							index2 = NoeVec4()
							for a in range(4):
								ID = bs.readUShort()
								index2[a] = ID
								ID = ID // 3
								if len(g1m.boneMapList[info[2]]) > ID:
									ID = g1m.boneMapList[info[2]][ID]
								index[a] = ID
							mesh.skinIndiceList.append(index)
							mesh.oldSkinIndiceList.append(index2)
						elif element.typeHandler in [0x000D,0x0D00]:
							index = NoeVec4()
							index2 = NoeVec4()
							for a in range(4):
								ID = bs.readUByte()
								index2[a] = ID
								ID = ID // 3
								if len(g1m.boneMapList[info[2]]) > ID:
									ID = g1m.boneMapList[info[2]][ID]
								index[a] = ID
							mesh.skinIndiceList.append(index)
							mesh.oldSkinIndiceList.append(index2)
						else:
							print("unknown indices type handler... " + str(element.typeHandler))
						if (n != info[11] - 1):
							bs.seek(currentPos + buffer.strideSize)
		if len(boneList) > 0 and (len(mesh.oldSkinIndiceList) == 0 or len(mesh.skinWeightList) == 0):
			if len(mesh.oldSkinIndiceList) == 0:
				mesh.oldSkinIndiceList = [NoeVec4([0, 0, 0, 0]) for n in range(info[11])]
				mesh.skinIndiceList = [NoeVec4([0, 0, 0, 0]) for n in range(info[11])]
				mesh.hasNoBoneIndice = True
			if len(mesh.skinWeightList) == 0:
				mesh.skinWeightList = [NoeVec4([1, 0, 0, 0]) for n in range(info[11])]
				mesh.hasNoBoneWeight = True
			
		indiceBuffer = g1m.indiceBufferList[info[7]]
		bs.seek(indiceBuffer.offset + info[12] * indiceBuffer.strideSize)
		mat.IDStart = info[12]
		mat.IDCount = info[13]
		mat.idxType = indiceBuffer.strideSize
		if info[9] == 3:
			mat.primType = noesis.RPGEO_TRIANGLE
		elif info[9] == 4:
			mat.primType = noesis.RPGEO_TRIANGLE_STRIP
		else:
			print('Unknown primitive types')
		mesh.matList.append(mat)
		numIdx = info[13]
		if indiceBuffer.strideSize == 1:
			mesh.idxBuff += bs.readBytes(numIdx)
		elif indiceBuffer.strideSize == 2:
			mesh.idxBuff += bs.readBytes(numIdx * 2)
		elif indiceBuffer.strideSize == 4:
			mesh.idxBuff += bs.readBytes(numIdx * 4)
		else:
			print('indices type problem at offset:', bs.tell(), mat.idxType)

	submeshesIndex = []
	isClothType1List = {}
	isClothType2List = {}
	ID2s = {}
	for lod in g1m.lodList[0].list:
		for index in lod.indices:
			submeshesIndex.append(index)
			isClothType1List[index] = lod.ID & 0xF == 1
			isClothType2List[index] = lod.ID & 0xF == 2
			ID2s[index] = lod.ID2 & 0xF
	submeshesIndex = list(set(submeshesIndex))
	KeepDrawing = True
	currentMesh = 0
	if(len(submeshesIndex)>0):
		submeshesCount = max(submeshesIndex)
	else:
		KeepDrawing = False
		print("Skeleton g1m")
	print("Adding submeshes")
	rootFixFlag = False
	for i, mesh in enumerate(meshList):
		if not KeepDrawing:
			break
		if (isClothType2List[currentMesh] and (bComputeCloth or noesis.optWasInvoked("-g1mcloth"))):
			for v in range(mesh.vertCount):
				if (g1m.meshInfoList[currentMesh][2] < len(g1m.boneMapListCloth) and len(mesh.oldSkinIndiceList) > v):
					if (mesh.oldSkinIndiceList[v][0] // 3 < len(
							g1m.boneMapListCloth[g1m.meshInfoList[currentMesh][2]])):
						index = g1m.boneMapListCloth[g1m.meshInfoList[currentMesh][2]][
							mesh.oldSkinIndiceList[v][0] // 3]
						if (index != 0 and index < len(boneList)):
							quat1 = boneList[index].getMatrix().toQuat()
							quat2 = NoeQuat([0 - quat1[0], 0 - quat1[1], 0 - quat1[2], quat1[3]]) * NoeQuat(
								[mesh.vertPosBuff[v][0], mesh.vertPosBuff[v][1], mesh.vertPosBuff[v][2], 0]) * quat1
							mesh.vertPosBuff[v] = boneList[index].getMatrix()[3] + NoeVec3(
								[quat2[0], quat2[1], quat2[2]])
							rootFixFlag = True
							mesh.skinWeightList[v] = NoeVec4()
							mesh.skinIndiceList[v] = NoeVec4()
		if (isClothType1List[currentMesh] and (bComputeCloth or noesis.optWasInvoked("-g1mcloth"))):
			nunoMap = clothMap[ID2s[currentMesh]]
			count = mesh.vertCount
			if (len(mesh.binormalBuffer) > 0):
				rootFixFlag = True
				for v in range(count):
					if (mesh.binormalBuffer[v] == NoeVec4()):
						mesh.vertPosBuff[v] = boneList[
							g1m.boneMapList[g1m.meshInfoList[currentMesh][2]][0]].getMatrix().transformPoint(
							mesh.vertPosBuff[v])
						mesh.vertNormBuff[v] = boneList[
							g1m.boneMapList[g1m.meshInfoList[currentMesh][2]][0]].getMatrix().transformNormal(
							mesh.vertNormBuff[v])
						continue
					clothPosition = NoeVec4([mesh.vertPosBuff[v][0], mesh.vertPosBuff[v][1], mesh.vertPosBuff[v][2],
											 mesh.clothStuff3Buffer[v]])
					position = NoeVec3()
					d4 = NoeVec3()
					d4 += processClothVertex(position, clothPosition, mesh.oldSkinIndiceList[v], nunoMap) * \
						  mesh.skinWeightList[v][0]
					d4 += processClothVertex(position, clothPosition, mesh.clothStuff1Buffer[v], nunoMap) * \
						  mesh.skinWeightList[v][1]
					d4 += processClothVertex(position, clothPosition, mesh.fogBuffer[v], nunoMap) * \
						  mesh.skinWeightList[v][2]
					d4 += processClothVertex(position, clothPosition, mesh.clothStuff2Buffer[v], nunoMap) * \
						  mesh.skinWeightList[v][3]

					d5 = NoeVec3()
					d5 += processClothVertex(position, clothPosition, mesh.oldSkinIndiceList[v], nunoMap) * \
						  mesh.clothStuff5Buffer[v][0]
					d5 += processClothVertex(position, clothPosition, mesh.clothStuff1Buffer[v], nunoMap) * \
						  mesh.clothStuff5Buffer[v][1]
					d5 += processClothVertex(position, clothPosition, mesh.fogBuffer[v], nunoMap) * \
						  mesh.clothStuff5Buffer[v][2]
					d5 += processClothVertex(position, clothPosition, mesh.clothStuff2Buffer[v], nunoMap) * \
						  mesh.clothStuff5Buffer[v][3]

					d6 = NoeVec3()
					d6 += processClothVertex(position, mesh.binormalBuffer[v], mesh.oldSkinIndiceList[v], nunoMap) * \
						  mesh.skinWeightList[v][0]
					d6 += processClothVertex(position, mesh.binormalBuffer[v], mesh.clothStuff1Buffer[v], nunoMap) * \
						  mesh.skinWeightList[v][1]
					d6 += processClothVertex(position, mesh.binormalBuffer[v], mesh.fogBuffer[v], nunoMap) * \
						  mesh.skinWeightList[v][2]
					d6 += processClothVertex(position, mesh.binormalBuffer[v], mesh.clothStuff2Buffer[v], nunoMap) * \
						  mesh.skinWeightList[v][3]

					mesh.vertPosBuff[v] = d5.cross(d6) * mesh.clothStuff4Buffer[v] + d4
					mesh.skinWeightList[v] = NoeVec4()
					mesh.skinIndiceList[v] = NoeVec4()

		finalVertexPosBuffer = bytes()
		finalVertexUVBuffer = bytes()
		finalVertexNormBuffer = bytes()
		finalIndiceList = bytes()
		finalWeightList = bytes()
		finalColorBuffer = bytes()
		finalTangentBuffer = bytes()
		if currentMesh in morphMap:
			finalMorphBuffers = [bytes() for morph in morphMap[currentMesh]]
		else:
			finalMorphBuffers = []
		endianC = '>' if endian else ''
		# Positions
		if (mesh.vertCount is None):
			break
		for v in range(mesh.vertCount):
			vertex = mesh.vertPosBuff[v]
			if(not rootFixFlag):
				vertex += boneList[0].getMatrix()[3]
			for k in range(3):
				finalVertexPosBuffer += noePack(endianC + 'f', vertex[k])
			if currentMesh in morphMap:
				for index,morph in enumerate(morphMap[currentMesh]):
					morphVertex = morph[v] + vertex
					for k in range(3):
						finalMorphBuffers[index] += noePack(endianC + 'f', morphVertex[k] + G1HOffset*(index+1) if k==0 else morphVertex[k])
		# Normals
		for v in range(mesh.vertCount):
			vertex = mesh.vertNormBuff[v]
			for k in range(3):
				finalVertexNormBuffer += noePack(endianC + 'f', vertex[k])
		# UVs
		for v in range(mesh.vertCount):
			vertex = mesh.vertUVBuff[v]
			for k in range(2):
				finalVertexUVBuffer += noePack(endianC + 'f', vertex[k])
		# tangents
		if (len(mesh.tangentBuffer) != 0):
			for v in range(mesh.vertCount):
				vertex = mesh.tangentBuffer[v]
				for k in range(4):
					finalTangentBuffer += noePack(endianC + 'f', vertex[k])
		# colors
		# for v in range(mesh.vertCount):
		# vertex = mesh.colorBuffer[v]
		# for k in range(4):
		# finalColorBuffer+=noePack(endianC + 'f',vertex[k])
		
		# Weights
		if not mesh.hasNoBoneWeight:
			for v in range(mesh.vertCount):
				vertex = mesh.skinWeightList[v]
				for k in range(4):
					finalWeightList += noePack(endianC + 'f', vertex[k])
		# Bone indices
		if not mesh.hasNoBoneIndice:
			for v in range(mesh.vertCount):
				vertex = mesh.skinIndiceList[v]
				for k in range(4):
					finalIndiceList += noePack(endianC + 'H', int(vertex[k]) & 0xFFFF)

		rapi.rpgBindPositionBuffer(finalVertexPosBuffer, noesis.RPGEODATA_FLOAT, 12)
		rapi.rpgBindUV1Buffer(finalVertexUVBuffer, noesis.RPGEODATA_FLOAT, 8)
		rapi.rpgBindNormalBuffer(finalVertexNormBuffer, noesis.RPGEODATA_FLOAT, 12)
		# rapi.rpgBindColorBuffer(finalColorBuffer, noesis.RPGEODATA_FLOAT,16,4)
		# if(len(mesh.tangentBuffer)>0):
		# rapi.rpgBindTangentBuffer(finalTangentBuffer,noesis.RPGEODATA_FLOAT,16)

		if not mesh.hasNoBoneIndice:
			rapi.rpgBindBoneIndexBuffer(finalIndiceList, noesis.RPGEODATA_USHORT, 8, 4)
		if not mesh.hasNoBoneWeight:
			rapi.rpgBindBoneWeightBuffer(finalWeightList, noesis.RPGEODATA_FLOAT, 16, 4)

		for j, mat in enumerate(mesh.matList):
			meshName = 'submesh_' + str(currentMesh)
			material = NoeMaterial(meshName, "")
			if len(textureList) > 0:
				if diffID > -1:
					print("Found Diffuse Texture %s" % (mat.diffuse))
					material.setTexture(mat.diffuse)
				if normID > -1:
					print("Found Normal Texture %s" % (mat.normal))
					material.setNormalTexture(mat.normal)
			else:
				matName = mat.diffuse
			rapi.rpgSetMaterial(meshName)
			rapi.rpgSetName(meshName)
			matList.append(material)
			if (currentMesh >= submeshesCount):
				KeepDrawing = False
			print("submesh " + str(currentMesh + 1) + "/" + str(submeshesCount + 1))
			if not bDisplayCloth and (isClothType2List[currentMesh] or isClothType1List[currentMesh]):
				currentMesh += 1
				continue
			
			if mat.idxType == 1: rapi.rpgCommitTriangles(mesh.idxBuff[mat.IDStart:mat.IDStart + mat.IDCount],
														 noesis.RPGEODATA_UBYTE, mat.IDCount, mat.primType, 1)
			elif mat.idxType == 2: rapi.rpgCommitTriangles(
				mesh.idxBuff[mat.IDStart * 2:mat.IDStart * 2 + mat.IDCount * 2], noesis.RPGEODATA_USHORT, mat.IDCount,
				mat.primType, 1)
			elif mat.idxType == 4: rapi.rpgCommitTriangles(
				mesh.idxBuff[mat.IDStart * 4:mat.IDStart * 4 + mat.IDCount * 4], noesis.RPGEODATA_UINT, mat.IDCount,
				mat.primType, 1)
			
			if bLoadG1H or noesis.optWasInvoked("-g1mmorph"):
				for index,morph in enumerate(finalMorphBuffers):
					rapi.rpgClearBufferBinds()
					rapi.rpgSetMaterial(meshName)
					rapi.rpgSetName(meshName+'_morph_' + str(index))
					rapi.rpgBindPositionBuffer(morph, noesis.RPGEODATA_FLOAT, 12)
					rapi.rpgBindUV1Buffer(finalVertexUVBuffer, noesis.RPGEODATA_FLOAT, 8)
					rapi.rpgBindNormalBuffer(finalVertexNormBuffer, noesis.RPGEODATA_FLOAT, 12)
					
					if mat.idxType == 1: rapi.rpgCommitTriangles(mesh.idxBuff[mat.IDStart:mat.IDStart + mat.IDCount],
															 noesis.RPGEODATA_UBYTE, mat.IDCount, mat.primType, 1)
					elif mat.idxType == 2: rapi.rpgCommitTriangles(
						mesh.idxBuff[mat.IDStart * 2:mat.IDStart * 2 + mat.IDCount * 2], noesis.RPGEODATA_USHORT, mat.IDCount,
						mat.primType, 1)
					elif mat.idxType == 4: rapi.rpgCommitTriangles(
						mesh.idxBuff[mat.IDStart * 4:mat.IDStart * 4 + mat.IDCount * 4], noesis.RPGEODATA_UINT, mat.IDCount,
						mat.primType, 1)
				
				
			rootFixFlag = False
			currentMesh += 1

	finalDriverMeshes = []
	if (bDisplayDrivers or noesis.optWasInvoked("-g1mdriver")):
		for j, mesh in enumerate(driverMeshList):
			if (mesh.vertCount is None):
				break

			tris = []
			for v in range(len(mesh.triangles)):
				triangle = mesh.triangles[v]
				for k in range(3):
					tris.append(triangle[k])
			finalWeights = []
			for index, weight in zip(mesh.skinIndiceList, mesh.skinWeightList):
				indices = []
				weights = []
				for k in range(4):
					indices.append(int(index[k]))
					weights.append(weight[k])
				finalWeights.append(NoeVertWeight(indices, weights))

			drivmesh = NoeMesh(tris, mesh.vertPosBuff)
			drivmesh.setPositions(mesh.vertPosBuff)
			drivmesh.setWeights(finalWeights)
			drivmesh.setName("driverMesh " + str(j))
			print("driverMesh_" + str(j + 1) + "/" + str(len(driverMeshList)))
			finalDriverMeshes.append(drivmesh)

	try:
		mdl = rapi.rpgConstructModel()
	except:
		mdl = NoeModel()
	if(len(submeshesIndex))>0:
		mdl.meshes = mdl.meshes + tuple(finalDriverMeshes)
	if len(meshList) > 0:
		mdl.setModelMaterials(NoeModelMaterials(textureList, matList))
	if len(boneList) > 0:
		# boneList = rapi.multiplyBones(boneList)
		mdl.setBones(boneList)
	if len(animationList) > 0:
		mdl.setAnims(animationList)
		rapi.setPreviewOption("setAnimSpeed", str(globalFramerate))
	mdlList.append(mdl)

	return 1
