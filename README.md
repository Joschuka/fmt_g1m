# FMT_G1M
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Noesis plugin to import G1M model files, G1T texture file, G1A and G2A skeletal animation files. 

## Setup

Simply put the python files in the plugins/python/ folder, next to the others.

## This plugin is still experimental, some models and animations may not work. For some particular models, it may take some time to load and it may seem that Noesis crashed but it will work eventually. If there isn't any error, just wait.

### Options

You can find the different options at the beginning of the fmt_g1m.py file. If you want to hide some meshes or see some info about the model, go to Tools/Data Viewer. You may want to close the Data Viewer before loading another model since it will take more time to load.
Some of the options have console commands equivalents to make exporting easier, you can find them at the beginning of the file.

* bLog

Display the Noesis log. It will show some progress and information about the import.

* bComputeCloth

Fix the cloth vertices' positions. Clothes will only be well-placed in T-pose and won't be animated since they are supposed to be simulated at runtime.

* bDisplayCloth

Render the cloth meshes. You may want to put it to False when previewing animations for example. 

* bDisplayDrivers

Render the cloth drivers and physics bones.

* bLoadG1T

Enable choosing a g1t texture file. Choosing a wrong one will lead to errors. Only single g1t files are supported for now, if the model needs several ones extract the g1t and the g1m separately.

* bLoadG1MS

Enable choosing another g1m which contains the skeleton. Choosing a wrong one or not choosing one for a model needing one will lead to errors.

* bLoadG1MSOnly

Only Load the skeleton.

* bLoadG1MOid

Enable choosing an `Oid.bin` file which contains the bone names for the skeleton.

* bAutoLoadG1MS

Load the first g1m in the same folder as a skeleton. Put it to False when using model merging.

* bLoadG1AG2A

Enable choosing a g1a/g2a file which contains animation. Choosing a wrong one will display an error message. You can add several ones, one after another.

* bLoadG1AG2AFolder

Enable choosing a folder from which all g1a/g2a files will be loaded.

* bLoadG1H

Enable choosing a folder from which contains morph targets/shapekeys. You can choose the offset between these with the G1HOffset parameter.

### Model merging

If you want to combine models, follow these steps :
* put all the desired models in the same folder. If the skeleton g1m is in a separate file, put it in another folder.
* make sure to put bAutoLoadG1MS to False and bLoadG1MS to True.
* right click on the first g1m and choose model merge. Noesis will then load all the models of the same format located next to the one selected. They will be loaded one after another, choose the texture file, skeleton and animations for each one of them (most of the time you'll have to choose the same skeleton and animations for all of them)

The model merger can also be used to extract textures from several g1t files at the same time.

**If you only want the t-posed combined model, put the MERGE_BONES option to 1 at the top of the merge script, it will combine the skeletons. As of now it doesn't work for animations so keep it to 0 if you want combined meshes animated, it will have some duplicated bones. Textures will be duplicated too if the same g1t was use for all the models, I will correct it in the future**

### License
This library is available under GPL v3 license. (See LICENSE.md)