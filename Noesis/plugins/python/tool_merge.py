from inc_noesis import *
import os

# MERGE_BONES
# 0 = no collapsing
# 1 = collapse by name
# 2 = collapse by name and reapply relative transforms
# 3 = collapse by name and reapply relative transforms, retransforming geometry as well
MERGE_BONES = 1


def registerNoesisTypes():
	handle = noesis.registerTool("&Merger", mergeToolMethod,
								 "Merge all models of a given type and load them into a single scene")
	noesis.setToolFlags(handle, noesis.NTOOLFLAG_CONTEXTITEM)
	noesis.setToolVisibleCallback(handle, mergeContextVisible)
	return 1


def mergeContextVisible(toolIndex, selectedFile):
	if selectedFile is None or (
			noesis.getFormatExtensionFlags(os.path.splitext(selectedFile)[1]) & noesis.NFORMATFLAG_MODELREAD) == 0:
		return 0
	return 1


def mergeToolMethod(toolIndex):
	basePath = noesis.getSelectedFile()

	dstFilePath = noesis.getScenesPath() + "merger.noesis"
	with open(dstFilePath, "w") as f:
		f.write("NOESIS_SCENE_FILE\r\nversion 1\r\nphysicslib\t\t\"\"\r\ndefaultAxis\t\t\"0\"\r\n\r\n")
		dirName = os.path.dirname(basePath)
		baseFileName, baseFileExt = os.path.splitext(basePath)
		dirList = os.listdir(dirName)
		numObj = 0
		for fileName in dirList:
			n, ext = os.path.splitext(fileName)
			if ext == baseFileExt:
				f.write("object\r\n{\r\n")
				f.write("\tname\t\t\"node" + "%i" % numObj + "\"\r\n")
				f.write("\tmodel\t\t\"" + dirName + "\\" + fileName + "\"\r\n")
				if numObj > 0:
					f.write("\tmergeTo\t\t\"node0\"\r\n")
					if MERGE_BONES != 0:
						f.write("\tmergeBones\t\t\"" + "%i" % MERGE_BONES + "\"\r\n")
				f.write("}\r\n")
				numObj += 1
	if noesis.openAndRemoveTempFile(dstFilePath) is not True:
		noesis.messagePrompt("Could not open merged model file!")
	return 0
