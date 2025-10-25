#-----------------------------------------------------------------
#    SCRIPT           spPaint3dGui2025.py
#    AUTHOR           Sebastien Paviot
#                     spaviot@gmail.com
#    DATE:            July,August 2009 - April,May 2010
#
#    UPDATE
#                     Denes Dankhazi
#                     ddankhazi@gmail.com
#                     Oktober, 2025
#                     
#
#    DESCRIPTION:    Build Maya main tool and setup windows
#
#    VERSION:        2025
#
#-----------------------------------------------------------------

import maya.cmds as mc
import random as rand
import sys
import importlib
import webbrowser

# Standard Maya script import with reload support for Maya 2026 + Python 3
try:
    import spPaint3dContext2025
    importlib.reload(spPaint3dContext2025)
except ImportError:
    import spPaint3dContext2025

def getIconPath(iconName):
    userScriptDir = mc.internalVar(userScriptDir=True)
    return userScriptDir + 'icons/' + iconName

spPaint3dGuiID = "spPaint3d2025"
spPaint3dGuiID_Height = 750
spPaint3dSetupID = "spPaint3dSetup2025"
spPaint3dVersion = 2025.0

#debug to log some operation down to the script editor
sp3d_log = False


# optionVar name: (type, default value, corresponding class attribute)
# For now the class methods only check for 'iv' and 'fv' types while looping stuff
sp3dOptionVars = {
                    "sp3dTransformRotate": ("iv", 1, "transformRotate"),
                    "sp3dTransformScale": ("iv", 1, "transformScale"),
                    "sp3dTransformScaleUniform": ("iv", 1, "transformScaleUniform"),
                    "sp3dInstance": ("iv", 0, "instance"),
                    "sp3dRandom": ("iv", 1, "random"),
                    "sp3dAlign": ("iv", 1, "align"),
                    "sp3dPaintFlux": ("iv", 1, "paintFlux"),
                    "sp3dRampFX": ("fv", 0, "rampFX"),
                    "sp3dRealTimeRampFX": ("iv", 1, "realTimeRampFX"),
                    "sp3dAllowNegativeScale": ("iv", 0, "allowNegativeScale"),
                    "sp3dForceVisibility": ("iv", 1, "forceVisibility"),
                    "sp3dPaintTimer": ("fv", 0.05, "paintTimer"),
                    "sp3dPaintDistance": ("fv", 10, "paintDistance"),
                    "sp3dPaintOffset": ("fv", 0, "upOffset"),
                    "sp3dPlaceRotate": ("fv", 45, "placeRotate"),
                    "sp3dContinuousTransform": ("iv", 0, "continuousTransform"),
                    "sp3dJitter": ("iv", 0, "jitter"),
                    "sp3dJitterAlgorithm": ("iv", 1, "jitterAlgorithm"),
                    "sp3dPreserveInConn": ("iv", 1, "preserveConn"),
                    "sp3dSmoothNormal": ("iv", 1, "smoothNormal"),
                    "sp3dSetupHierarchy": ("iv", 1, "hierarchy"),
                    "sp3dGroup": ("fv", 0, "group"),
                    "sp3dSourceObjects": ("sv", "", "sourceObjects"),
                    "sp3dTargetObjects": ("sv", "", "targetObjects"),
                    "sp3dSourceWeights": ("sv", "", "sourceWeights"),
                    "sp3dVersion": ("fv", spPaint3dVersion, "version")
                }



class sp3dToolOption (object):
    '''
    Class to store all tool related data
    '''

    def __init__ (self):
        '''
        Build the object to store all variables.
        Initialize the default attributes and call the methods to update value from optionVars if necessary.
        '''
        self.transformRotate = True
        self.transformScale = True
        self.transformScaleUniform = True
        self.instance = False
        self.random = True
        self.align = True
        self.paintFlux = True #True=distance / False=timer
        self.jitter = False
        self.rampFX = 0 #0=none, 1=rotate, 2=scale, 3=both
        self.realTimeRampFX = True
        self.allowNegativeScale = False #True=allow negative scale values, False=clamp to 0.001 minimum
        self.forceVisibility = True #True=force duplicated objects to be visible, False=preserve original visibility
        self.paintTimer = 0.05
        self.paintDistance = 10
        self.placeRotate = 45
        self.rotateIncrementSnap = False #Paint mode rotate increment snap
        self.continuousTransform = False #Place mode only option, retransform cursor at every drag event
        self.upOffset = 0
        self.preserveConn = True
        self.smoothNormal = False #false=decal mode, force pure normal from intersected triangle / true=smoothed normal per neighboring edges
        self.hierarchy = True #True = grouping of painted objects enabled by default
        self.group = 0 #float value so it doesnt get converted into boolean when I batch read the Vars / 0=single group / 1=stroke group / 2=source group
        self.groupID = None #used to track the group name where to sort the generated objects from the paint strokes
        self.sourceWeights = {} #Dictionary to store object weights: {"objectName": weight_value}
        self.jitterAlgorithm = 1 #0=simple, 1=re-raycast (default)
        self.sourceObjects = "" #Serialized string of source objects for persistence
        self.targetObjects = "" #Serialized string of target objects for persistence
        self.version = spPaint3dVersion #used to allow tracking of potentially erroneous obsolete optionVars

        if(self.checkVars()):
            #all optionVars seem to be in proper condition, will fetch the stored data and update the instance attributes
            self.loadVars()
        else:
            #seems there are issues with the optionVars and/or version mismatch
            mc.confirmDialog(title='Script options alert', message='It seems either the script is run for the first time or the version running is different than the saved data.\nAll options will be reseted to defaults!', button=['Whatever'])

            #also deleting the main & setup windows prefs to avoid size issues across versions
            if mc.windowPref(spPaint3dSetupID, exists=True): mc.windowPref(spPaint3dSetupID, remove=True)
            if mc.windowPref(spPaint3dGuiID, exists=True): mc.windowPref(spPaint3dGuiID, remove=True)
             
            self.commitVars()


    def dumpVars (self):
        '''
        print the value of all the tool option
        '''
        print (self.__dict__)

    def checkVars (self):
        '''
        Method to check if the stored optionVars contain valid data, if any.
        Returns False if any issue is detected.
        Returns True if all conditions are met and the method runs its course.
        '''
        for name, info in sp3dOptionVars.items():    #loop through all the optionVars from the global struct
            #iterating through all the currently valid optionVar names from the global struct, then fetching the stored value if it exists
            var_type, value, varname = info
            if (not mc.optionVar(exists=name)):
                #name isnt' an existing optionVar
                return False
            if (name == 'sp3dVersion' and mc.optionVar(q=name) != value):
                #locally stored script version optionVar is obsolete
                return False

        #for loop exited before breaking, about to return True then
        return True

    def loadVars (self):
        '''
        Will load the stored optionVars into self
        '''
        for name, info in sp3dOptionVars.items():    #loop through all the optionVars from the global struct
            #iterating through all the currently valid optionVar names from the global struct, then fetching the stored value if it exists
            var_type, value, varname = info
            if (var_type == 'iv'):
                #this is an int value to convert into bool
                self.__dict__[varname] = bool(mc.optionVar(q=name))
            elif (var_type == 'fv'):
                self.__dict__[varname] = round(mc.optionVar(q=name), 2)
            elif (var_type == 'sv'):
                # Handle sourceWeights specially - don't load it as a string attribute
                if varname == 'sourceWeights':
                    continue  # Skip this, we'll handle it separately
                #string value 
                self.__dict__[varname] = mc.optionVar(q=name) if mc.optionVar(exists=name) else value

        # Convert sourceWeights string back to dictionary
        if sp3d_log: print("DEBUG: loadVars - calling loadSourceWeights")
        self.loadSourceWeights()
        if sp3d_log: print("DEBUG: loadVars - after loadSourceWeights: %s" % self.sourceWeights)
        
        if (sp3d_log): self.dumpVars()

    def loadSourceWeights(self):
        '''
        Convert the sourceWeights string from optionVar back to dictionary
        '''
        # Initialize sourceWeights as dictionary
        self.sourceWeights = {}
        
        # Get the string value directly from optionVar
        if mc.optionVar(exists="sp3dSourceWeights"):
            weightsString = mc.optionVar(q="sp3dSourceWeights")
            
            # Check for string types (Python 2/3 compatibility)
            if hasattr(weightsString, 'strip') and weightsString.strip():
                try:
                    # Parse the string format: objName1:weight1;objName2:weight2
                    for entry in weightsString.split(";"):
                        if entry.strip():
                            parts = entry.split(":")
                            if len(parts) == 2:
                                objName = parts[0].strip()
                                weight = float(parts[1].strip())
                                self.sourceWeights[objName] = weight
                                if sp3d_log: print("DEBUG: Loaded weight for %s: %s" % (objName, weight))
                except (ValueError, IndexError) as e:
                    if sp3d_log: print("DEBUG: Error loading source weights: %s" % str(e))
                    self.sourceWeights = {}
        
        # Ensure sourceWeights is always a dictionary
        if not isinstance(self.sourceWeights, dict):
            if sp3d_log: 
                sourceWeightsType = type(self.sourceWeights)
                print("DEBUG: Force-converting sourceWeights to dict, was: %s" % sourceWeightsType)
            self.sourceWeights = {}

    def saveSourceWeights(self):
        '''
        Convert the sourceWeights dictionary to string for optionVar storage
        Returns the string version without modifying self.sourceWeights
        '''
        if sp3d_log: 
            sourceWeightsAttr = getattr(self, 'sourceWeights', 'NOT_FOUND')
            sourceWeightsType = type(getattr(self, 'sourceWeights', None))
            print("DEBUG: saveSourceWeights called - sourceWeights: %s (type: %s)" % (sourceWeightsAttr, sourceWeightsType))
        
        if hasattr(self, 'sourceWeights') and isinstance(self.sourceWeights, dict) and self.sourceWeights:
            # Convert to string format: objName1:weight1;objName2:weight2
            weightEntries = []
            for objName, weight in self.sourceWeights.items():
                weightEntries.append("%s:%s" % (objName, weight))
            weightsString = ";".join(weightEntries)
            if sp3d_log: print("DEBUG: Generated weights string: %s" % weightsString)
            return weightsString
        else:
            if sp3d_log: print("DEBUG: sourceWeights empty or invalid, returning empty string")
            return ""


    def resetVars (self):
        '''
        Flush the values and restore default settings
        '''
        for name, info in sp3dOptionVars.items():    #loop through all the optionVars from the global struct
            #iterating through all the currently valid optionVar names from the global struct, then fetching the stored value if it exists
            var_type, value, varname = info
            if (var_type == 'iv'):
                #this is an int value to convert into bool
                mc.optionVar(iv=(name, value))
            elif (var_type == 'fv'):
                #float value default
                mc.optionVar(fv=(name, value))
            elif (var_type == 'sv'):
                #string value default
                mc.optionVar(sv=(name, value))

        self.loadVars()



    def commitVars (self):
        '''
        Method to store the data from instance attributes into optionVars.
        '''
        # Convert sourceWeights dictionary to string before saving
        if sp3d_log: 
            sourceWeightsType = type(self.sourceWeights)
            print("DEBUG: commitVars - sourceWeights before save: %s (type: %s)" % (self.sourceWeights, sourceWeightsType))
        
        # Save the current sourceWeights dictionary, then temporarily set it to string for optionVar saving
        originalSourceWeights = self.sourceWeights
        weightsString = self.saveSourceWeights()
        self.sourceWeights = weightsString  # Temporarily set to string for optionVar saving
        
        if sp3d_log:
            print("DEBUG: commitVars - weights string for saving: %s" % weightsString)
        
        #print self.__dict__
        for name, info in sp3dOptionVars.items():    #force initialize optionVars to defaults
            #print ('looping commitVar %s' %name)
            var_type, value, varname = info
            #print varname
            if (var_type == 'iv'):
                #convert the bool attribute value into an int
                #print int(self.__dict__[varname])
                mc.optionVar(iv=(name, int(self.__dict__[varname])))
            elif (var_type == 'fv'):
                #all other optionVar types
                mc.optionVar(fv=(name, self.__dict__[varname]))
            elif (var_type == 'sv'):
                #string value
                mc.optionVar(sv=(name, self.__dict__[varname]))
        
        # Restore sourceWeights back to dictionary format after saving
        self.sourceWeights = originalSourceWeights
        if sp3d_log:
            print("DEBUG: commitVars - restored sourceWeights to: %s (type: %s)" % (self.sourceWeights, type(self.sourceWeights)))
        
        if (sp3d_log): self.dumpVars()

    def saveObjectLists(self, sourceList, targetList, uiSourceList=None, uiTargetList=None):
        '''
        Save object lists to optionVars for persistence across sessions
        '''
        if sp3d_log: print("DEBUG: saveObjectLists called")
        
        # Serialize source objects - use UI list order to preserve user selection order
        sourceObjects = []
        
        # Get objects from UI list in the correct order (this preserves user selection order)
        if uiSourceList and mc.textScrollList(uiSourceList, exists=True):
            uiSourceItems = mc.textScrollList(uiSourceList, query=True, allItems=True) or []
            for objName in uiSourceItems:
                if mc.objExists(objName) and objName in sourceList.obj:
                    objData = sourceList.obj[objName]
                    # Include weight in serialized data - ensure sourceWeights is a dictionary
                    if not isinstance(self.sourceWeights, dict):
                        if sp3d_log: 
                            sourceWeightsType = type(self.sourceWeights)
                            print("DEBUG: sourceWeights is not a dict, fixing it: %s" % sourceWeightsType)
                        self.sourceWeights = {}
                    weight = self.sourceWeights.get(objName, 1.0)
                    sourceObjects.append("%s|%s|%s|%s|%s" % (objName, objData[1], objData[2], objData[3], weight))
                    if sp3d_log: print("DEBUG: Saving source object: %s" % objName)
        else:
            # Fallback to dictionary iteration if UI is not available
            for objName, objData in sourceList.obj.items():
                if mc.objExists(objName):
                    if not isinstance(self.sourceWeights, dict):
                        self.sourceWeights = {}
                    weight = self.sourceWeights.get(objName, 1.0)
                    sourceObjects.append("%s|%s|%s|%s|%s" % (objName, objData[1], objData[2], objData[3], weight))
                    if sp3d_log: print("DEBUG: Saving source object (fallback): %s" % objName)
        
        self.sourceObjects = ";".join(sourceObjects)
        
        # Serialize target objects - use UI list order to preserve user selection order  
        targetObjects = []
        
        # Get objects from UI list in the correct order (this preserves user selection order)
        if uiTargetList and mc.textScrollList(uiTargetList, exists=True):
            uiTargetItems = mc.textScrollList(uiTargetList, query=True, allItems=True) or []
            for objName in uiTargetItems:
                if mc.objExists(objName) and objName in targetList.obj:
                    objData = targetList.obj[objName]
                    targetObjects.append("%s|%s|%s|%s" % (objName, objData[1], objData[2], objData[3]))
                    if sp3d_log: print("DEBUG: Saving target object: %s" % objName)
        else:
            # Fallback to dictionary iteration if UI is not available
            for objName, objData in targetList.obj.items():
                if mc.objExists(objName):
                    targetObjects.append("%s|%s|%s|%s" % (objName, objData[1], objData[2], objData[3]))
                    if sp3d_log: print("DEBUG: Saving target object (fallback): %s" % objName)
        
        self.targetObjects = ";".join(targetObjects)
        
        if sp3d_log: 
            print("DEBUG: sourceObjects string: %s" % self.sourceObjects)
            print("DEBUG: targetObjects string: %s" % self.targetObjects)
        
        # Save to optionVars
        self.commitVars()

    def restoreObjectLists(self, sourceList, targetList):
        '''
        Restore object lists from optionVars if objects still exist in scene
        Returns True if any objects were restored
        '''
        if sp3d_log: print("DEBUG: restoreObjectLists called")
        if sp3d_log: print("DEBUG: self.sourceObjects = '%s'" % self.sourceObjects)
        if sp3d_log: print("DEBUG: self.targetObjects = '%s'" % self.targetObjects)
        
        objectsRestored = False
        
        # Restore source objects
        if self.sourceObjects:
            if sp3d_log: print("DEBUG: Restoring source objects...")
            for objEntry in self.sourceObjects.split(";"):
                if objEntry.strip():
                    if sp3d_log: print("DEBUG: Processing source entry: %s" % objEntry)
                    try:
                        parts = objEntry.split("|")
                        if len(parts) >= 6:  # We need at least 6 parts because first part is empty
                            # The format is: |objName|activation|proba|align|weight
                            # After split: ['', 'group1', 'bushHawthornAC', 'True', '0.5', 'Up', '1.0']
                            objName = "|" + "|".join(parts[1:-4])  # Reconstruct full path: |group1|bushHawthornAC
                            activation = parts[-4] == "True"       # True
                            proba = float(parts[-3])               # 0.5  
                            align = parts[-2]                      # Up
                            weight = float(parts[-1])             # 1.0
                            
                            if sp3d_log: print("DEBUG: Checking if object exists: %s" % objName)
                            # Only restore if object still exists
                            if mc.objExists(objName):
                                if sp3d_log: print("DEBUG: Object exists, adding to sourceList")
                                result, _ = sourceList.addObj(objName, activation=activation, proba=proba, align=align)
                                if result:
                                    # Only set weight if not already loaded from sourceWeights persistence
                                    if objName not in self.sourceWeights:
                                        self.sourceWeights[objName] = weight
                                        if sp3d_log: print("DEBUG: Set weight from sourceObjects: %s = %s" % (objName, weight))
                                    else:
                                        if sp3d_log: print("DEBUG: Weight already loaded from persistence: %s = %s" % (objName, self.sourceWeights[objName]))
                                    objectsRestored = True
                                    if sp3d_log: print("DEBUG: Successfully restored source: %s" % objName)
                            else:
                                if sp3d_log: print("DEBUG: Object does not exist: %s" % objName)
                        else:
                            if sp3d_log: print("DEBUG: Malformed source entry skipped (wrong number of parts): %s" % objEntry)
                    except (ValueError, IndexError):
                        # Skip malformed entries
                        if sp3d_log: print("DEBUG: Exception in processing source entry: %s" % objEntry)
                        continue
        else:
            if sp3d_log: print("DEBUG: No source objects to restore")
        
        # Restore target objects
        if self.targetObjects:
            if sp3d_log: print("DEBUG: Restoring target objects...")
            for objEntry in self.targetObjects.split(";"):
                if objEntry.strip():
                    if sp3d_log: print("DEBUG: Processing target entry: %s" % objEntry)
                    try:
                        parts = objEntry.split("|")
                        if len(parts) >= 5:  # We need at least 5 parts because first part is empty
                            # The format is: |objName|activation|proba|align
                            # After split: ['', 'pPlane1', 'True', '0.5', 'Up']
                            objName = "|" + "|".join(parts[1:-3])  # Reconstruct full path: |pPlane1
                            activation = parts[-3] == "True"       # True
                            proba = float(parts[-2])               # 0.5  
                            align = parts[-1]                      # Up
                            
                            if sp3d_log: print("DEBUG: Checking if target object exists: %s" % objName)
                            # Only restore if object still exists
                            if mc.objExists(objName):
                                if sp3d_log: print("DEBUG: Target object exists, adding to targetList")
                                result, _ = targetList.addObj(objName, activation=activation, proba=proba, align=align)
                                if result:
                                    objectsRestored = True
                                    if sp3d_log: print("DEBUG: Successfully restored target: %s" % objName)
                            else:
                                if sp3d_log: print("DEBUG: Target object does not exist: %s" % objName)
                        else:
                            if sp3d_log: print("DEBUG: Malformed target entry skipped (wrong number of parts): %s" % objEntry)
                    except (ValueError, IndexError):
                        # Skip malformed entries
                        if sp3d_log: print("DEBUG: Exception in processing target entry: %s" % objEntry)
                        continue
        else:
            if sp3d_log: print("DEBUG: No target objects to restore")
                        
        if sp3d_log: print("DEBUG: objectsRestored = %s" % objectsRestored)
        return objectsRestored

    def getGroupID (self):
        '''
        Called during the onRelease event of a stroke. This method manages a consistent unique group name throughout the paint strokes
        '''
        if (not self.groupID):
            #group is not yet created
            self.groupID = mc.group(empty=True, name='spPaint3dOutput')
        return self.groupID





class sp3dTransform (object):
    '''
    contains values for the transform options
    '''
    def __init__(self, rotate=((0, 0), (-360, 360), (0, 0)), scale=((1, 1), (1, 1), (1, 1)), uJitter=(-15,15), vJitter=(-15,15)):
        '''
        initialise attributes
        '''
        self.rotate = rotate
        self.scale = scale
        self.uJitter = uJitter
        self.vJitter = vJitter

    def getRandomRotate (self, uiValues=None):
        '''
        return a (x,y,z) tuple with properly randomized value between the self.rotate bounds
        '''
        x, y, z = self.rotate
        if uiValues and uiValues.rotateIncrementSnap and uiValues.placeRotate > 0:
            # Snap to increment logic
            randx = self.snapToIncrement(rand.uniform(x[0], x[1]), uiValues.placeRotate, x[0], x[1])
            randy = self.snapToIncrement(rand.uniform(y[0], y[1]), uiValues.placeRotate, y[0], y[1])
            randz = self.snapToIncrement(rand.uniform(z[0], z[1]), uiValues.placeRotate, z[0], z[1])
            randxyz = (round(randx, 3), round(randy, 3), round(randz, 3))
        else:
            # Original random behavior
            randxyz = (round(rand.uniform(x[0], x[1]), 3), round(rand.uniform(y[0], y[1]), 3), round(rand.uniform(z[0], z[1]), 3))
        return randxyz

    def snapToIncrement(self, value, increment, minVal, maxVal):
        '''
        Snap a value to the nearest increment within min/max bounds
        '''
        # Calculate the number of steps from minVal
        steps = round((value - minVal) / increment)
        # Calculate the snapped value
        snapped = minVal + (steps * increment)
        # Ensure it's within bounds
        return max(minVal, min(maxVal, snapped))

    def getRandomScale (self, uniform):
        '''
        return a (x,y,z) tuple with properly randomized value between the self.scale bounds
        '''
        x, y, z = self.scale
        if (uniform):
            randxyz = round(rand.uniform(x[0], x[1]), 3)
            return (randxyz, randxyz, randxyz)
        else:
            randxyz = (round(rand.uniform(x[0], x[1]), 3), round(rand.uniform(y[0], y[1]), 3), round(rand.uniform(z[0], z[1]), 3))
            return randxyz
    
    def getRandomJitter (self, space):
        '''
        return a random value between the min and max from the corresponding space. space must be either 'uJitter' or 'vJitter'
        '''
        min,max = self.__dict__[space]        
        return round(rand.uniform(min,max), 3)


class sp3dObjectList (object):
    '''
    store a dictionnary of objects, their DAG data and some other data
    dictionnary structure: { 'name as displayed in the list, also the name of the transform' : 'fullDAGPath', Activation bool (default True), Probability float (default 50%), Align Override (default UpAxis either be Y or Z)}
    '''
     #define the list of authorized object type used when adding objects to lists
    authType = {
        'default': ('mesh',),
        'source': ('mesh', 'locator',),
        'target': ('mesh',)
    }

    def __init__(self, authorized='target', errorHandle=None):
        '''
        initialize the default attributes.
        INPUT:     authorized = specify the type of authorized geometry for that list, fetched from the authType class attributes
                    valid values :    default / source / target (defined as class attributes)
        '''
        #TODO
        self.obj = {} #dictionnary of entries
        self.i = 0 #index values used if this is a source object list using sequential mode distribution
        self.auth = self.authType[authorized] #used to sort 'valid' object when using the add method
        self.errorHandle = errorHandle

    def validateObjects(self):
        if not self.obj: 
            return False

        for obj, data in self.obj.items():
            # NE raiseError-t hivj itt
            if self.errorHandle and hasattr(self.errorHandle, "logInfo"):
                self.errorHandle.logInfo("validating object: %s" % data[0])
            else:
                # safe fallback
                print("INFO: validating object: %s" % data[0])

            n = data[0]
            # FIX: None vagy ures nev eseten ne hivd az objExists-et
            if not n or not mc.objExists(n):
                # probald meg feloldani a leszarmazott rajzolhato node-ot (static asset lanc miatt)
                kids = mc.listRelatives(obj, ad=True, f=True) or []
                found = None
                for k in kids:
                    t = mc.nodeType(k)
                    if t in ("mesh", "gpuCache", "AlembicNode", "alembicHolder"):
                        if mc.objExists(k):
                            found = (mc.ls(k, long=True) or [k])[0]
                            break
                if found:
                    # irjuk vissza a talalt draw node-ot
                    if isinstance(data, list):
                        data[0] = found
                    elif isinstance(data, tuple):
                        self.obj[obj] = (found,) + data[1:]
                else:
                    return False

        if self.errorHandle and hasattr(self.errorHandle, "logInfo"):
            self.errorHandle.logInfo("Everything checks out")
        else:
            print("INFO: Everything checks out")
        return True


    def hasDuplicate(self, compareobjlist):
        '''
        Return True of there's any object from self found in the 'compareobjlist' dictionnary
        Return False if all objects are unique
        (In context: there can't be an object which is both a source object and a target surface)
        '''
        for obj, data in compareobjlist.obj.items():
            if(self.alreadyExists(obj)): return True
        return False

    def alreadyExists(self, obj):
        '''
        check if obj already exists in the self.dictionnary (namespace-safe)
        '''
        import maya.cmds as mc
        long_name = (mc.ls(obj, long=True) or [obj])[0]
        return long_name in self.obj

    def addObj(self, obj=None, dagPath=None, activation=True, proba=0.5, align='Up'):
        """
        Append an entry to self.obj for any DAG object that has a transform.
        Now supports groups as well as individual objects.

        INPUT:
            obj       = node name (shape or transform components are ok, will be resolved)
            dagPath   = optional full DAG path if points to a shape, its parent transform will be used
            activation= whether this source is active in the pool
            proba     = probability used when randomizing sources
            align     = axis override for on-surface alignment

        RETURN:
            (key, True) on success, where key is the transform's full DAG path
            (None, "reason") on failure
        """
        import maya.cmds as mc

        # --- helpers ----------------------------------------------------------------
        def _as_node(n):
            """Resolve components/short names to a node name if possible."""
            if not n:
                return None
            # ls(objectsOnly=True) strips components like pCube1.f[0]
            lst = mc.ls(n, objectsOnly=True, long=True) or mc.ls(n, objectsOnly=True) or []
            return lst[0] if lst else None

        def _ensure_transform(n):
            """Return (transform_long_path, None) or (None, reason)."""
            if not n or not mc.objExists(n):
                return None, "Object does not exist"
            # If already a transform, normalize to long path
            if mc.nodeType(n) == 'transform':
                long_n = (mc.ls(n, long=True) or [n])[0]
                return long_n, None
            # For shapes or other DAG types, climb one level to parent transform
            parents = mc.listRelatives(n, parent=True, fullPath=True) or []
            for p in parents:
                if mc.nodeType(p) == 'transform':
                    return p, None
            return None, "Object has no transform parent"

        def _is_group(n):
            """Check if transform is a group (has children but no shapes)."""
            if mc.nodeType(n) != 'transform':
                return False
            # Check if it has shape children - if yes, it's not a group
            shapes = mc.listRelatives(n, children=True, shapes=True) or []
            if shapes:
                return False
            # Check if it has transform children - if yes, it's a group
            children = mc.listRelatives(n, children=True, type='transform') or []
            return len(children) > 0

        # --- resolve input to a transform -------------------------------------------
        node = _as_node(dagPath) or _as_node(obj)
        if not node:
            return None, "No valid object specified"

        xform, err = _ensure_transform(node)
        if err:
            return None, err

        # Use the full DAG path of the transform as the dictionary key (namespace-safe)
        key = (mc.ls(xform, long=True) or [xform])[0]

        # Prevent duplicates
        if self.alreadyExists(key):
            return None, "Object already exists in the list and can't be added again"

        # Handle groups differently from individual objects
        if _is_group(xform):
            # For groups, store ONLY the group transform itself (not the children)
            # This ensures that when selected, the entire group gets duplicated as one unit
            self.obj[key] = (key, activation, proba, align)
        else:
            # For individual objects, use the shape path if it exists, otherwise the transform
            shapePath = getDAGPath(key, True)
            if shapePath:
                self.obj[key] = (shapePath, activation, proba, align)
            else:
                # Fallback to transform if no valid shape found (e.g., for locators or other non-mesh objects)
                self.obj[key] = (key, activation, proba, align)

        return key, True


    def printObj(self):
        '''
        print the content of the dictionnary (namespace-safe)
        mostly used for debug purpose
        '''
        for obj, data in self.obj.items():
            print("%s : %s" % (obj, data))

    def delObj(self, obj=None):
        '''
        delete obj from the self.obj dictionnary
        '''
        #TODO: check if key really exists return False
        #TODO: delete the key:data and return True
        del self.obj[obj]

    def clrObj(self):
        '''
        empty the dictionnary
        '''
        self.obj = {}
        self.i = 0

    def getRandom(self, weighted=False, sourceWeights=None):
        '''
        will return a random entry dagMesh from the dictionnary.
        will return a weighted random entry using the sourceWeights dict if weighted=True
        will return None if the method was unsuccessful to retrieve the selected object (if object was deleted from the scene while the script was running for example)
        '''
        dkeys = list(self.obj.keys())
        
        if weighted and sourceWeights:
            # Ensure sourceWeights is a dictionary
            if not isinstance(sourceWeights, dict):
                if sp3d_log: 
                    sourceWeightsType = type(sourceWeights)
                    print("DEBUG: sourceWeights parameter is not a dict in getRandom: %s" % sourceWeightsType)
                sourceWeights = {}
            # Weighted random selection
            objects = []
            weights = []
            
            for key in dkeys:
                dag = self.obj[key][0]  # Get the DAG path (shape node)
                
                # Try to match weight by transform name (parent of shape)
                import maya.cmds as mc
                if mc.objExists(dag):
                    # Get the transform parent if dag is a shape
                    if mc.nodeType(dag) != 'transform':
                        parents = mc.listRelatives(dag, parent=True, fullPath=True) or []
                        if parents:
                            transform_dag = parents[0]
                        else:
                            transform_dag = dag
                    else:
                        transform_dag = dag
                    
                    # Try different name formats for weight lookup
                    weight = sourceWeights.get(transform_dag, None)  # Full path
                    if weight is None:
                        short_name = transform_dag.split('|')[-1]  # Short name
                        weight = sourceWeights.get(short_name, 1.0)
                else:
                    weight = 1.0
                
                objects.append(dag)
                weights.append(weight)

            
            # Use weighted random selection (Python 2 compatible)
            import random
            total_weight = sum(weights)
            if total_weight <= 0:
                # Fallback to equal weights if all weights are 0 or negative
                selected = objects[random.randint(0, len(objects) - 1)]
            else:
                # Create cumulative weights
                cumulative_weights = []
                cumulative = 0
                for weight in weights:
                    cumulative += weight
                    cumulative_weights.append(cumulative)
                
                # Generate random number and find selection
                rand_val = random.uniform(0, total_weight)
                for i, cum_weight in enumerate(cumulative_weights):
                    if rand_val <= cum_weight:
                        selected = objects[i]
                        break
                else:
                    # Fallback (should not happen)
                    selected = objects[-1]
            
            return selected
        else:
            # Original random selection
            dag = self.obj[dkeys[rand.randint(0, len(dkeys) - 1)]]
            return dag[0]

    def getNext(self):
        '''
        will return the dagMesh of the next entry in the dictionnary. will increment the index by 1 (index will be calculated modulo the dictionnary length will polling for the next entry).
        will return None if the method was unsuccessful to retrieve the selected object (if object was deleted from the scene while the script was running for example)
        '''
        #TODO: implement boolean flag
        dkeys = list(self.obj.keys())
        dkeys.sort()
        dag = self.obj[dkeys[self.i % len(dkeys)]]
        self.i += 1
        return dag[0]





class sp3derror (object):
    '''
    class used to raise script error during the execution and display runtime info to the user in the bottom textfield of the main UI
    '''
    def __init__(self, initerror, uifield):
        '''
        initialise default attributes
        '''
        self.error = initerror
        self.ui = uifield
        self.broadcastError()

    def broadcastError(self):
        '''
        display the error in the proper field in the UI (self.uiInfoTextField)
        '''
        mc.textField(self.ui, edit=True, text=self.error)

    def raiseError(self, newerror):
        '''
        update the error and call out to display it in the main UI
        '''
        self.error = newerror
        self.broadcastError()


class spPaint3dWin2025 (object):
    '''
    Main UI window class definition
    '''
    def __init__(self):
        #delete ui window if opened
        if mc.window(spPaint3dGuiID, exists=True): mc.deleteUI(spPaint3dGuiID)
        #removing delete prefs to prevent issues when window is spawned outside of display on mac?
        #if mc.windowPref(spPaint3dGuiID, exists=True): mc.windowPref(spPaint3dGuiID, remove=True)
        
        #delete option window if opened
        if mc.window(spPaint3dSetupID, exists=True):
            mc.deleteUI(spPaint3dSetupID)
        
        self.mayaVersion = getMayaVersion()
        
        self.uiWin = mc.window(spPaint3dGuiID, title=("spPaint3d | " + str(spPaint3dVersion)), width=255, resizeToFitChildren=True, sizeable=True, titleBar=True, minimizeButton=False, maximizeButton=False, menuBar=False, menuBarVisible=False, toolbox=True)
        
        self.uiTopColumn = mc.columnLayout(adjustableColumn=True, columnAttach=('both', 5))
        
        #----------------------
        # Top buttons
        #----------------------
        self.uiTopForm = mc.formLayout(numberOfDivisions=100)
        self.uiBtnHelp = mc.button(label='Help', command=lambda * args:self.uiButtonCallback("uiBtnHelp", args))
        self.uiBtnOptions = mc.button(label='Options', command=lambda * args:self.uiButtonCallback("uiBtnOptions", args))
        
        mc.formLayout(self.uiTopForm, edit=True, attachControl=[(self.uiBtnOptions, 'left', 5, self.uiBtnHelp)])
        
        mc.setParent(self.uiTopColumn)
        
        #----------------------
        # Source Frame
        #----------------------
        self.uiSourceFrame = mc.frameLayout(label='Brush Geometry', cll=True, collapseCommand=lambda:self.resizeWindow('collapse', 98), expandCommand=lambda:self.resizeWindow('expand', 98), mh=5, mw=5)
        self.uiSourceForm = mc.formLayout(numberOfDivisions=100, width=255)
        self.uiSourceList = mc.textScrollList(numberOfRows=5, allowMultiSelection=True, width=250, selectCommand=lambda: self.uiSourceSelectionCallback())
        self.uiSourceBtnAdd = mc.symbolButton(w=60, h=18, ann='Add selected object(s) to the list', image=getIconPath('sp3dadd.xpm'), command=lambda * args:self.uiListCallback("add", "uiSourceList"))
        self.uiSourceBtnRem = mc.symbolButton(w=60, h=18, ann='Remove selected object(s) from the list', image=getIconPath('sp3drem.xpm'), command=lambda * args:self.uiListCallback("rem", "uiSourceList"))
        self.uiSourceBtnClr = mc.symbolButton(w=60, h=18, ann='Clear the list', image=getIconPath('sp3dclr.xpm'), command=lambda * args:self.uiListCallback("clr", "uiSourceList"))
        
        # Weight panel
        self.uiSourceWeightSeparator = mc.separator(height=8, width=250, style='in')
        self.uiSourceWeightLabel = mc.text(label='Selected Weight:', align='left', height=20, backgroundColor=(0.3, 0.3, 0.3))
        self.uiSourceWeightField = mc.floatFieldGrp(label='Weight:', precision=2, w=250, cw=[(1, 60), (2, 80)], v1=1.0, step=0.1, changeCommand=lambda * args:self.uiSourceWeightCallback(args), enable=False)
        
        mc.formLayout(self.uiSourceForm, edit=True, 
                     attachForm=[(self.uiSourceList, 'top', 0), (self.uiSourceList, 'left', 0), (self.uiSourceList, 'right', 0),
                                (self.uiSourceBtnAdd, 'left', 0),
                                (self.uiSourceWeightSeparator, 'left', 0), (self.uiSourceWeightSeparator, 'right', 0),
                                (self.uiSourceWeightLabel, 'left', 5), (self.uiSourceWeightLabel, 'right', 5),
                                (self.uiSourceWeightField, 'left', 5), (self.uiSourceWeightField, 'right', 5)], 
                     attachControl=[(self.uiSourceBtnAdd, 'top', 3, self.uiSourceList),
                                   (self.uiSourceBtnRem, 'left', 5, self.uiSourceBtnAdd), (self.uiSourceBtnRem, 'top', 3, self.uiSourceList), 
                                   (self.uiSourceBtnClr, 'left', 5, self.uiSourceBtnRem), (self.uiSourceBtnClr, 'top', 3, self.uiSourceList),
                                   (self.uiSourceWeightSeparator, 'top', 8, self.uiSourceBtnAdd),
                                   (self.uiSourceWeightLabel, 'top', 8, self.uiSourceWeightSeparator),
                                   (self.uiSourceWeightField, 'top', 5, self.uiSourceWeightLabel)])
        
        mc.setParent(self.uiTopColumn)
        
        #----------------------
        # Transform Setup
        #----------------------
        self.uiTransformFrame = mc.frameLayout(label='Transform Setup', cll=True, collapseCommand=lambda:self.resizeWindow('collapse', 200), expandCommand=lambda:self.resizeWindow('expand', 200), mh=5, mw=5)
        self.uiTransformForm = mc.formLayout(numberOfDivisions=100, width=255)
        self.uiTransformRotateCheck = mc.checkBox(label='Rotate', ann='Activate the rotate transform while painting', changeCommand=lambda * args:self.uiCheckBoxCallback("transformRotate", args))
        self.uiTransformRotateFieldX = mc.floatFieldGrp(numberOfFields=2, label='Min', backgroundColor=(.81, .24, 0), extraLabel='Max', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), changeCommand=lambda * args:self.uiTransformCallback())
        self.uiTransformRotateFieldY = mc.floatFieldGrp(numberOfFields=2, label=' ', backgroundColor=(.41, .75, 0), extraLabel=' ', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), changeCommand=lambda * args:self.uiTransformCallback(), v1=-360, v2=360)
        self.uiTransformRotateFieldZ = mc.floatFieldGrp(numberOfFields=2, label=' ', backgroundColor=(.17, .4, .63), extraLabel=' ', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), changeCommand=lambda * args:self.uiTransformCallback())
        self.uiRotateIncrementSnapCheck = mc.checkBox(label='Enable Rotation Snap', ann='Snap rotation values to increment steps in both paint and place modes', changeCommand=lambda * args:self.uiRotateIncrementSnapCallback(args))
        self.uiRotateIncrement = mc.floatFieldGrp(label='Rotate Increment', precision=2, w=250, cw=[(1, 100), (2, 50)], v1=45, step=1, changeCommand=lambda * args:self.uiRotateIncrementCallback("placeRotate", args))
        self.uiTransformSeparator = mc.separator(height=5, width=250, style='in')
        self.uiTransformScaleCheck = mc.checkBox(label='Scale', ann='Activate the scale transform while painting', changeCommand=lambda * args:self.uiCheckBoxCallback("transformScale", args))
        self.uiTransformScaleUniformCheck = mc.checkBox(label='Uniform', ann='Force uniform scale while painting', changeCommand=lambda * args:self.uiCheckBoxCallback("transformScaleUniform", args))
        self.uiTransformScaleFieldX = mc.floatFieldGrp(numberOfFields=2, label='Min', backgroundColor=(.81, .24, 0), extraLabel='Max', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), v1=1.0, v2=1.0, step=0.1, changeCommand=lambda * args:self.uiTransformCallback())
        self.uiTransformScaleFieldY = mc.floatFieldGrp(numberOfFields=2, label=' ', backgroundColor=(.41, .75, 0), extraLabel=' ', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), v1=1.0, v2=1.0, step=0.1, changeCommand=lambda * args:self.uiTransformCallback())
        self.uiTransformScaleFieldZ = mc.floatFieldGrp(numberOfFields=2, label=' ', backgroundColor=(.17, .4, .63), extraLabel=' ', cw4=(32, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), v1=1.0, v2=1.0, step=0.1, changeCommand=lambda * args:self.uiTransformCallback())
        
        mc.formLayout(self.uiTransformForm, edit=True,
            attachForm=[(self.uiTransformRotateCheck, 'top', 4), (self.uiTransformRotateFieldX, 'top', 0)],
            attachControl=[    (self.uiTransformRotateFieldX, 'left', 10, self.uiTransformRotateCheck),
                            (self.uiTransformRotateFieldY, 'top', 5, self.uiTransformRotateFieldX), (self.uiTransformRotateFieldY, 'left', 10, self.uiTransformRotateCheck),
                            (self.uiTransformRotateFieldZ, 'top', 5, self.uiTransformRotateFieldY), (self.uiTransformRotateFieldZ, 'left', 10, self.uiTransformRotateCheck),
                            (self.uiRotateIncrementSnapCheck, 'top', 5, self.uiTransformRotateFieldZ), (self.uiRotateIncrementSnapCheck, 'left', 10, self.uiTransformRotateCheck),
                            (self.uiRotateIncrement, 'top', 5, self.uiRotateIncrementSnapCheck), (self.uiRotateIncrement, 'left', 10, self.uiTransformRotateCheck),
                            (self.uiTransformSeparator, 'top', 5, self.uiRotateIncrement), (self.uiTransformScaleCheck, 'top', 5, self.uiTransformSeparator), (self.uiTransformScaleUniformCheck, 'top', 5, self.uiTransformScaleCheck),
                            (self.uiTransformScaleFieldX, 'top', 5, self.uiTransformSeparator), (self.uiTransformScaleFieldX, 'left', 15, self.uiTransformScaleCheck),
                            (self.uiTransformScaleFieldY, 'top', 5, self.uiTransformScaleFieldX), (self.uiTransformScaleFieldY, 'left', 15, self.uiTransformScaleCheck),
                            (self.uiTransformScaleFieldZ, 'top', 5, self.uiTransformScaleFieldY), (self.uiTransformScaleFieldZ, 'left', 15, self.uiTransformScaleCheck),
                            ])
        
        mc.setParent(self.uiTopColumn)
        self.transform = sp3dTransform()
        
        #----------------------
        # Target Surface(s)
        #----------------------
        self.uiTargetFrame = mc.frameLayout(label='Target Surface(s)', cll=True, collapseCommand=lambda:self.resizeWindow('collapse', 98), expandCommand=lambda:self.resizeWindow('expand', 98), mh=5, mw=5)
        self.uiTargetForm = mc.formLayout(numberOfDivisions=100, width=255)
        self.uiTargetList = mc.textScrollList(numberOfRows=5, allowMultiSelection=True, width=250)
        self.uiTargetBtnAdd = mc.symbolButton(w=60, h=18, ann='Add selected object(s) to the list', image=getIconPath('sp3dadd.xpm'), command=lambda * args:self.uiListCallback("add", "uiTargetList"))
        self.uiTargetBtnRem = mc.symbolButton(w=60, h=18, ann='Remove selected object(s) from the list', image=getIconPath('sp3drem.xpm'), command=lambda * args:self.uiListCallback("rem", "uiTargetList"))
        self.uiTargetBtnClr = mc.symbolButton(w=60, h=18, ann='Clear the list', image=getIconPath('sp3dclr.xpm'), command=lambda * args:self.uiListCallback("clr", "uiTargetList"))
        
        mc.formLayout(self.uiTargetForm, edit=True, attachForm=[(self.uiTargetList, 'top', 0)], attachControl=[(self.uiTargetBtnAdd, 'top', 3, self.uiTargetList), (self.uiTargetBtnRem, 'left', 5, self.uiTargetBtnAdd), (self.uiTargetBtnRem, 'top', 3, self.uiTargetList), (self.uiTargetBtnClr, 'left', 5, self.uiTargetBtnRem), (self.uiTargetBtnClr, 'top', 3, self.uiTargetList)])
        
        mc.setParent(self.uiTopColumn)
        
        #----------------------
        # Paint Contexts
        #----------------------
        self.uiPaintFrame = mc.frameLayout(label='Paint', cll=True, collapseCommand=lambda:self.resizeWindow('collapse', 61), expandCommand=lambda:self.resizeWindow('expand', 61), mh=5, mw=5)
        self.uiPaintForm = mc.formLayout(numberOfDivisions=100, width=255)
        self.uiPaintDupSCB = mc.symbolCheckBox(w=52, h=18, ann='Duplicate: Instance or Copy', ofi=getIconPath('sp3dduplicate.xpm'), oni=getIconPath('sp3dinstance.xpm'), changeCommand=lambda * args:self.uiCheckBoxCallback("instance", args))
        self.uiPaintRandSCB = mc.symbolCheckBox(w=52, h=18, ann='Object distribution: Random or Sequential', ofi=getIconPath('sp3dsequence.xpm'), oni=getIconPath('sp3drandom.xpm'), changeCommand=lambda * args:self.uiCheckBoxCallback("random", args))
        self.uiPaintAlignSCB = mc.symbolCheckBox(w=100, h=18, ann='Align generated objects to the target surface', ofi=getIconPath('sp3dalignoff.xpm'), oni=getIconPath('sp3dalign.xpm'), changeCommand=lambda * args:self.uiCheckBoxCallback("align", args))
        self.uiPaintCtxBtn = mc.symbolButton(w=105, h=28, ann='Paint', image=getIconPath('sp3dpaint.xpm'), command=lambda * args:self.genericContextCallback("PaintCtx"))
        self.uiPlaceCtxBtn = mc.symbolButton(w=105, h=28, ann='Place', image=getIconPath('sp3dplace.xpm'), command=lambda * args:self.genericContextCallback("PlaceCtx"))
        
        mc.formLayout(self.uiPaintForm, edit=True,
                        attachForm=[(self.uiPaintDupSCB, 'top', 0)],
                        attachControl=[    (self.uiPaintRandSCB, 'left', 5, self.uiPaintDupSCB), (self.uiPaintAlignSCB, 'left', 5, self.uiPaintRandSCB),
                                         (self.uiPaintCtxBtn, 'top', 5, self.uiPaintDupSCB), (self.uiPlaceCtxBtn, 'top', 5, self.uiPaintDupSCB), (self.uiPlaceCtxBtn, 'left', 5, self.uiPaintCtxBtn)])
        
        mc.setParent(self.uiTopColumn)
        
        #----------------------
        # Paint Metrics
        #----------------------
        self.uiPaintMetricsFrame = mc.frameLayout(label='Paint Options', cll=True, collapseCommand=lambda:self.resizeWindow('collapse', 129), expandCommand=lambda:self.resizeWindow('expand', 129), mh=5, mw=5)
        self.uiPaintMetricsForm = mc.formLayout(numberOfDivisions=100, width=255)
        self.uiPaintTimer = mc.floatSliderGrp(label='Sensibility', field=1, minValue=0.0, maxValue=0.2, fieldMaxValue=1.0, precision=2, vis=False, w=250, cw=[(1, 55), (2, 35)], changeCommand=lambda * args:self.uiFluxCallback("paintTimer", args))
        self.uiPaintDistance = mc.floatFieldGrp(label='Distance threshold', precision=4, vis=False, w=250, cw=[(1, 100), (2, 50)], step=0.001, changeCommand=lambda * args:self.uiFluxCallback("paintDistance", args))
        self.uiPaintMetricsSep1 = mc.separator(w=250)
        self.uiUpOffset = mc.floatFieldGrp(label='Up Offset', precision=2, vis=True, w=100, cw=[(1, 54), (2, 40)], changeCommand=lambda * args:self.uiPaintOffsetCallback("upOffset", args))
        self.uiPaintMetricsRampMenu = mc.optionMenu(l='Ramp FX', changeCommand=lambda * args:self.uiRampMenuCallback("rampMenu", args))
        mc.menuItem(label=' ')
        mc.menuItem(label='rotate')
        mc.menuItem(label='scale')
        mc.menuItem(label='both')
        self.uiPaintMetricsSep2 = mc.separator(w=250)


        self.uiJitterCheck = mc.checkBox(label='Jitter', ann='Activate jitter transform along U & V while painting', changeCommand=lambda * args:self.uiCheckBoxCallback("jitter", args))
        self.uiJitterFieldU = mc.floatFieldGrp(numberOfFields=2, label='MinU', backgroundColor=(.895, .735, 0.176), extraLabel='Max', cw4=(40, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), v1=-15, v2=15, step=0.1, changeCommand=lambda * args:self.uiTransformCallback())
        self.uiJitterFieldV = mc.floatFieldGrp(numberOfFields=2, label='MinV', backgroundColor=(.692, .323, 0.851), extraLabel='Max', cw4=(40, 50, 50, 40), precision=2, ct4=('right', 'both', 'both', 'right'), co4=(2, 2, 2, 8), v1=-15, v2=15, step=0.1, changeCommand=lambda * args:self.uiTransformCallback())
        
        mc.formLayout(self.uiPaintMetricsForm, edit=True,
                        attachForm=[(self.uiPaintTimer, 'top', 0), (self.uiPaintDistance, 'top', 0),(self.uiUpOffset, 'left', 0)],
                        attachControl=[(self.uiPaintMetricsSep1, 'top', 5, self.uiPaintTimer), (self.uiPaintMetricsSep1, 'top', 5, self.uiPaintDistance), (self.uiUpOffset, 'top', 5, self.uiPaintMetricsSep1),(self.uiPaintMetricsRampMenu, 'top', 6, self.uiPaintMetricsSep1),(self.uiPaintMetricsRampMenu, 'left', 10, self.uiUpOffset),
                                       (self.uiPaintMetricsSep2, 'top', 5, self.uiUpOffset)])

        mc.formLayout(self.uiPaintMetricsForm, edit=True,
            attachControl=[ (self.uiJitterCheck, 'top', 5,self.uiPaintMetricsSep2), (self.uiJitterFieldU, 'left', 5, self.uiJitterCheck),(self.uiJitterFieldU, 'top', 5, self.uiPaintMetricsSep2),
                            (self.uiJitterFieldV, 'top', 5, self.uiJitterFieldU), (self.uiJitterFieldV, 'left', 5, self.uiJitterCheck)])

        
        mc.setParent(self.uiTopColumn)
        
        
        #----------------------
        # Footer
        #----------------------
        self.uiInfoFrame = mc.frameLayout(labelVisible=False)
        self.uiInfoTextField = mc.textField(editable=False)
        self.errorHandle = sp3derror((spPaint3dGuiID + ' | Sebastien Paviot/Denes Dankhazi'), self.uiInfoTextField)
        
        #----------------------
        # Update UI controls
        #----------------------
        self.uiValues = sp3dToolOption()
        self.updateUIControls(self.uiValues)
        
        #----------------------
        # Source & Target object lists
        #----------------------
        self.sourceList = sp3dObjectList('source')
        self.targetList = sp3dObjectList('target')
        
        # Restore previously saved object lists if any objects still exist
        if sp3d_log: print("DEBUG: About to call restoreObjectLists")
        restored = self.uiValues.restoreObjectLists(self.sourceList, self.targetList)
        if sp3d_log: print("DEBUG: restoreObjectLists returned: %s" % restored)
        if restored:
            if sp3d_log: print("DEBUG: Calling updateObjectListUI")
            self.updateObjectListUI()
            if sp3d_log:
                print("spPaint3d: Restored object lists from previous session")
        else:
            if sp3d_log: print("DEBUG: No objects were restored")
        
        #----------------------
        # Context tracking
        #----------------------
        self.ctx = None
        
        mc.showWindow(self.uiWin)
        self.resizeWindow('winui', spPaint3dGuiID_Height) # force a resize to prevent some weird UI issue on mac
        if(sp3d_log): self.debugFrameSize() #display actual corrected ui frame sizes
        

    def uiTransformCallback(self, *args):
        '''
        rebuild the transform combo tuple and feed the class when changed in the UI
        '''
        rotate = ((mc.floatFieldGrp(self.uiTransformRotateFieldX, q=True, v1=True), mc.floatFieldGrp(self.uiTransformRotateFieldX, q=True, v2=True)), (mc.floatFieldGrp(self.uiTransformRotateFieldY, q=True, v1=True), mc.floatFieldGrp(self.uiTransformRotateFieldY, q=True, v2=True)), (mc.floatFieldGrp(self.uiTransformRotateFieldZ, q=True, v1=True), mc.floatFieldGrp(self.uiTransformRotateFieldZ, q=True, v2=True)))
        
        # Get scale values and validate based on allowNegativeScale setting
        scaleXMin = mc.floatFieldGrp(self.uiTransformScaleFieldX, q=True, v1=True)
        scaleXMax = mc.floatFieldGrp(self.uiTransformScaleFieldX, q=True, v2=True)
        scaleYMin = mc.floatFieldGrp(self.uiTransformScaleFieldY, q=True, v1=True)
        scaleYMax = mc.floatFieldGrp(self.uiTransformScaleFieldY, q=True, v2=True)
        scaleZMin = mc.floatFieldGrp(self.uiTransformScaleFieldZ, q=True, v1=True)
        scaleZMax = mc.floatFieldGrp(self.uiTransformScaleFieldZ, q=True, v2=True)
        
        # Apply minimum value clamping only if negative scale is not allowed
        if not self.uiValues.allowNegativeScale:
            scaleXMinClamped = max(0.001, scaleXMin)
            scaleXMaxClamped = max(0.001, scaleXMax)
            scaleYMinClamped = max(0.001, scaleYMin)
            scaleYMaxClamped = max(0.001, scaleYMax)
            scaleZMinClamped = max(0.001, scaleZMin)
            scaleZMaxClamped = max(0.001, scaleZMax)
            
            # Update GUI if values were changed
            if scaleXMinClamped != scaleXMin or scaleXMaxClamped != scaleXMax:
                mc.floatFieldGrp(self.uiTransformScaleFieldX, e=True, v1=scaleXMinClamped, v2=scaleXMaxClamped)
            if scaleYMinClamped != scaleYMin or scaleYMaxClamped != scaleYMax:
                mc.floatFieldGrp(self.uiTransformScaleFieldY, e=True, v1=scaleYMinClamped, v2=scaleYMaxClamped)
            if scaleZMinClamped != scaleZMin or scaleZMaxClamped != scaleZMax:
                mc.floatFieldGrp(self.uiTransformScaleFieldZ, e=True, v1=scaleZMinClamped, v2=scaleZMaxClamped)
        else:
            # Allow negative values - use original values
            scaleXMinClamped = scaleXMin
            scaleXMaxClamped = scaleXMax
            scaleYMinClamped = scaleYMin
            scaleYMaxClamped = scaleYMax
            scaleZMinClamped = scaleZMin
            scaleZMaxClamped = scaleZMax
        
        scale = ((scaleXMinClamped, scaleXMaxClamped), (scaleYMinClamped, scaleYMaxClamped), (scaleZMinClamped, scaleZMaxClamped))
        uJitter = ((mc.floatFieldGrp(self.uiJitterFieldU, q=True, v1=True), mc.floatFieldGrp(self.uiJitterFieldU, q=True, v2=True))) 
        vJitter = ((mc.floatFieldGrp(self.uiJitterFieldV, q=True, v1=True), mc.floatFieldGrp(self.uiJitterFieldV, q=True, v2=True)))
        self.transform = sp3dTransform(rotate, scale, uJitter, vJitter)
        self.updateCtx()

    def uiRampMenuCallback(self, *args):
        '''
        ramp effect menu stuff
        '''
        if args[1][0]=='rotate': self.uiValues.rampFX = 1
        elif args[1][0]=='scale': self.uiValues.rampFX = 2
        elif args[1][0]=='both': self.uiValues.rampFX = 3
        else: self.uiValues.rampFX = 0
        self.uiValues.commitVars()
        self.updateCtx()


    def uiTransformReset(self):
        '''
        reset transform values and update UI
        '''
        self.transform = sp3dTransform()
        mc.floatFieldGrp(self.uiTransformRotateFieldX, e=True, v1=0, v2=0)
        mc.floatFieldGrp(self.uiTransformRotateFieldY, e=True, v1=-360, v2=360)
        mc.floatFieldGrp(self.uiTransformRotateFieldZ, e=True, v1=0, v2=0)
        mc.floatFieldGrp(self.uiTransformScaleFieldX, e=True, v1=1, v2=1)
        mc.floatFieldGrp(self.uiTransformScaleFieldY, e=True, v1=1, v2=1)
        mc.floatFieldGrp(self.uiTransformScaleFieldZ, e=True, v1=1, v2=1)

        mc.floatFieldGrp(self.uiJitterFieldU, e=True, v1=-15, v2=15)
        mc.floatFieldGrp(self.uiJitterFieldV, e=True, v1=-15, v2=15)
        mc.floatFieldGrp(self.uiRotateIncrement, e=True, v1=45)


    def uiFluxCallback(self, *args):
        '''
        Callback for timer slider and distance float field change
        INPUT: [variable name, (value to update,)]
        '''
        value = float(args[1][0])
        
        # Clamp paintDistance to minimum 0.001 to prevent negative values and division by zero
        if args[0] == "paintDistance" and value < 0.001:
            value = 0.001
            # Update GUI field to show corrected value
            mc.floatFieldGrp(self.uiPaintDistance, edit=True, v1=value)
        
        self.uiValues.__dict__[args[0]] = value
        self.uiValues.commitVars()
        self.updateCtx()


    def uiPaintOffsetCallback(self, *args):
        '''
        Callback for paint Offset field change
        INPUT: [variable name, (value to update,)]
        '''
        self.uiValues.__dict__[args[0]] = float(args[1][0])
        self.uiValues.commitVars()
        self.updateCtx()

    def uiRotateIncrementCallback(self, *args):
        '''
        Callback for rotate increment field change
        INPUT: [variable name, (value to update,)]
        '''
        self.uiValues.__dict__[args[0]] = float(args[1][0])
        self.uiValues.commitVars()
        self.updateCtx()

    def uiSourceSelectionCallback(self):
        '''
        Callback when source list selection changes
        '''
        selectedItems = mc.textScrollList(self.uiSourceList, query=True, selectItem=True)
        if selectedItems and len(selectedItems) >= 1:
            # Ensure sourceWeights is a dictionary before accessing
            if not isinstance(self.uiValues.sourceWeights, dict):
                if sp3d_log: 
                    sourceWeightsType = type(self.uiValues.sourceWeights)
                    print("DEBUG: sourceWeights is not a dict in selection callback, fixing it: %s" % sourceWeightsType)
                self.uiValues.sourceWeights = {}
            
            # Single or multiple selection - enable weight field
            if len(selectedItems) == 1:
                # Single selection - show exact weight
                selectedObject = selectedItems[0]
                weight = self.uiValues.sourceWeights.get(selectedObject, 1.0)
                mc.floatFieldGrp(self.uiSourceWeightField, edit=True, enable=True, v1=weight)
                mc.text(self.uiSourceWeightLabel, edit=True, label='Weight for %s:' % selectedObject)
            else:
                # Multiple selection - show average weight
                weights = [self.uiValues.sourceWeights.get(obj, 1.0) for obj in selectedItems]
                avgWeight = sum(weights) / len(weights)
                mc.floatFieldGrp(self.uiSourceWeightField, edit=True, enable=True, v1=avgWeight)
                mc.text(self.uiSourceWeightLabel, edit=True, label='Weight for %s objects:' % len(selectedItems))
        else:
            # No selection - disable weight field
            mc.floatFieldGrp(self.uiSourceWeightField, edit=True, enable=False, v1=1.0)
            mc.text(self.uiSourceWeightLabel, edit=True, label='Selected Weight:')

    def uiSourceWeightCallback(self, *args):
        '''
        Callback when weight field changes
        '''
        selectedItems = mc.textScrollList(self.uiSourceList, query=True, selectItem=True)
        if selectedItems:
            # Ensure sourceWeights is a dictionary before accessing
            if not isinstance(self.uiValues.sourceWeights, dict):
                if sp3d_log: 
                    sourceWeightsType = type(self.uiValues.sourceWeights)
                    print("DEBUG: sourceWeights is not a dict in weight callback, fixing it: %s" % sourceWeightsType)
                self.uiValues.sourceWeights = {}
            
            # Maya floatFieldGrp callback returns ((value,),) format
            newWeight = float(args[0][0]) 
            if sp3d_log: 
                print("DEBUG: uiSourceWeightCallback - setting weight %s for objects: %s" % (newWeight, selectedItems))
            
            # Apply new weight to all selected objects
            for selectedObject in selectedItems:
                self.uiValues.sourceWeights[selectedObject] = newWeight
                if sp3d_log:
                    print("DEBUG: Set weight for '%s': %s" % (selectedObject, newWeight))
            
            if sp3d_log:
                print("DEBUG: sourceWeights after setting: %s" % self.uiValues.sourceWeights)
            
            # Save updated weights to sourceObjects string
            self.uiValues.saveObjectLists(self.sourceList, self.targetList, self.uiSourceList, self.uiTargetList)
            self.uiValues.commitVars()

    def uiRotateIncrementSnapCallback(self, *args):
        '''
        Callback for rotate increment snap checkbox
        '''
        # Maya checkbox callback returns ((True,),) or ((False,),)
        value = args[0][0]  # Extract the actual boolean value
        self.uiValues.rotateIncrementSnap = value
        # Note: Rotate increment field stays always enabled for place mode
        self.uiValues.commitVars()
        self.updateCtx()

    def uiButtonCallback(self, *args):
        '''
        Callback for top buttons
        INPUT: [variable name]
        '''
        button = args[0]
        if (button == 'uiBtnHelp'):
            mc.confirmDialog(title=spPaint3dGuiID + ' ' + str(spPaint3dVersion) + ' Help', message='Please refer to the included spPaint3d_ReadMe.html file for detailed help on how to use the script.\n Or use the Homepage button in the Options.', button='Whatever')
        elif (button == 'uiBtnOptions'):
            self.setupWin(self.uiValues)

    def uiCheckBoxCallback(self, *args):
        '''
        Callback for checkbox and symbolCheckbox
        INPUT: [variable name, (string value for bool state,)]
        '''
        if (sp3d_log): print ('input from UI: %s of type %s' % (args, args[1][0].__class__))
        self.uiValues.__dict__[args[0]] = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        self.uiValues.commitVars()
        self.updateCtx()


    def updateUIControls(self, ui):
        '''
        Will update the self ui controls with the values stores in the passed instance object
        '''
        mc.checkBox(self.uiTransformRotateCheck, edit=True, value=ui.transformRotate)
        mc.checkBox(self.uiTransformScaleCheck, edit=True, value=ui.transformScale)
        mc.checkBox(self.uiTransformScaleUniformCheck, edit=True, value=ui.transformScaleUniform)
        mc.checkBox(self.uiJitterCheck, edit=True, value=ui.jitter)
        mc.symbolCheckBox(self.uiPaintDupSCB, edit=True, value=ui.instance)
        mc.symbolCheckBox(self.uiPaintRandSCB, edit=True, value=ui.random)
        mc.symbolCheckBox(self.uiPaintAlignSCB, edit=True, value=ui.align)

        # toggling the proper paint flux control
        mc.floatSliderGrp(self.uiPaintTimer, edit=True, visible=(not ui.paintFlux), value=ui.paintTimer)
        mc.floatFieldGrp(self.uiPaintDistance, edit=True, visible=ui.paintFlux, v1=ui.paintDistance)

        # feeding place rotate threshold
        mc.floatFieldGrp(self.uiUpOffset, edit=True, visible=True, v1=ui.upOffset)
        mc.floatFieldGrp(self.uiRotateIncrement, edit=True, v1=ui.placeRotate)
        
        # feeding rotate increment snap
        mc.checkBox(self.uiRotateIncrementSnapCheck, edit=True, value=ui.rotateIncrementSnap)
        # Rotate increment field stays always enabled for place mode usage

        if ui.rampFX==1: mc.optionMenu(self.uiPaintMetricsRampMenu, edit=True, value='rotate')
        elif ui.rampFX==2: mc.optionMenu(self.uiPaintMetricsRampMenu, edit=True, value='scale')
        elif ui.rampFX==3: mc.optionMenu(self.uiPaintMetricsRampMenu, edit=True, value='both')
        else: mc.optionMenu(self.uiPaintMetricsRampMenu, edit=True, value=' ')

    def updateObjectListUI(self):
        '''
        Update the UI lists with objects from sourceList and targetList
        Maintains the order from saved data (sourceObjects/targetObjects strings)
        '''
        if sp3d_log: print("DEBUG: updateObjectListUI called")
        # Clear existing UI lists first
        mc.textScrollList(self.uiSourceList, edit=True, removeAll=True)
        mc.textScrollList(self.uiTargetList, edit=True, removeAll=True)
        
        # Populate source list in the order they were saved
        if hasattr(self.uiValues, 'sourceObjects') and self.uiValues.sourceObjects:
            if sp3d_log: print("DEBUG: Using saved sourceObjects order")
            if sp3d_log: print("DEBUG: sourceObjects string: %s" % self.uiValues.sourceObjects)
            for i, objEntry in enumerate(self.uiValues.sourceObjects.split(";")):
                if objEntry.strip():
                    try:
                        # Extract object name from the entry format: |objName|activation|proba|align|weight
                        parts = objEntry.split("|")
                        if len(parts) >= 6:
                            objName = "|" + "|".join(parts[1:-4])  # Reconstruct full path
                            if sp3d_log: print("DEBUG: Processing entry %d: %s -> objName: %s" % (i, objEntry, objName))
                            if objName in self.sourceList.obj:
                                mc.textScrollList(self.uiSourceList, edit=True, append=objName)
                                if sp3d_log: print("DEBUG: Added to UI list: %s" % objName)
                            else:
                                if sp3d_log: print("DEBUG: Object not in sourceList: %s" % objName)
                    except Exception as e:
                        if sp3d_log: print("DEBUG: Error parsing entry %s: %s" % (objEntry, str(e)))
                        continue
        else:
            # Fallback to dictionary order if no saved data
            if sp3d_log: print("DEBUG: Using dictionary order fallback")
            for objName in self.sourceList.obj.keys():
                mc.textScrollList(self.uiSourceList, edit=True, append=objName)
            
        # Populate target list in the order they were saved
        if hasattr(self.uiValues, 'targetObjects') and self.uiValues.targetObjects:
            for objEntry in self.uiValues.targetObjects.split(";"):
                if objEntry.strip():
                    try:
                        # Extract object name from the entry format: |objName|activation|proba|align
                        parts = objEntry.split("|")
                        if len(parts) >= 5:
                            objName = "|" + "|".join(parts[1:-3])  # Reconstruct full path
                            if objName in self.targetList.obj:
                                mc.textScrollList(self.uiTargetList, edit=True, append=objName)
                    except:
                        continue
        else:
            # Fallback to dictionary order if no saved data
            for objName in self.targetList.obj.keys():
                mc.textScrollList(self.uiTargetList, edit=True, append=objName)

    def debugFrameSize(self):
        '''
        Will query and print the actual size of the frame to collapse. Will already remove 21 from the total height, so ready to use with the resizeWindow onCollapse command
        '''
        print ("sourceFrame: %i" % (mc.frameLayout(self.uiSourceFrame, query=True, height=True) - 21))
        print ("transformFrame: %i" % (mc.frameLayout(self.uiTransformFrame, query=True, height=True) - 21))
        print ("targetFrame: %i" % (mc.frameLayout(self.uiTargetFrame, query=True, height=True) - 21))
        print ("paintFrame: %i" % (mc.frameLayout(self.uiPaintFrame, query=True, height=True) - 21))
        print ("paintMetricFrame: %i" % (mc.frameLayout(self.uiPaintMetricsFrame, query=True, height=True) - 21))

    def resizeWindow(self, direction, offset):
        '''
        Will adjust the size of the window, used when collapsing/expanding frames
        '''
        if mc.window(spPaint3dGuiID, exists=True):
            currentSize = mc.window(self.uiWin, query=True, height=True)
            if (direction == 'collapse'):
                currentSize -= offset
            elif (direction == 'expand'):
                currentSize += offset
            elif (direction == 'winui'):
                currentSize = offset
            if(currentSize > 0):
                mc.window(self.uiWin, edit=True, height=currentSize)
        
        #self.debugFrameSize()

    def updateCtx(self):
        '''
        method to check if there's any running context to update
        '''
        if (self.ctx):
            #there's a context object that can be updated
            self.ctx.runtimeUpdate(self.uiValues, self.transform, self.sourceList, self.targetList)


    def uiListCallback(self, *args):
        '''
        textScrollList callback to manage the addition/removal/reset of the source & target object lists (namespace-safe)
        '''
        mode = args[0]
        textlist = args[1]
        if (textlist == 'uiSourceList'): objlist = 'sourceList'
        else: objlist = 'targetList'

        import maya.cmds as mc

        if (mode == 'add'):
            # ADD (always use long names)
            objselected = mc.ls(selection=True, long=True)
            for obj in objselected:
                addresult, addcomment = self.__dict__[objlist].addObj(obj)
                if (addresult is None):
                    self.errorHandle.raiseError(addcomment)
                else:
                    if (mc.objExists(addresult)):
                        mc.textScrollList(self.__dict__[textlist], edit=True, append=addresult)
                        # Add default weight for source objects
                        if textlist == 'uiSourceList':
                            self.uiValues.sourceWeights[addresult] = 1.0

        elif(mode == 'clr'):
            # CLEAR
            mc.textScrollList(self.__dict__[textlist], edit=True, removeAll=True)
            self.__dict__[objlist].clrObj()
            # Clear weights for source objects
            if textlist == 'uiSourceList':
                self.uiValues.sourceWeights.clear()

        elif(mode == 'rem'):
            # REMOVE (always use long names)
            remlist = mc.textScrollList(self.__dict__[textlist], query=True, selectItem=True)
            if(remlist):
                for remobj in remlist:
                    long_name = (mc.ls(remobj, long=True) or [remobj])[0]
                    self.__dict__[objlist].delObj(long_name)
                    mc.textScrollList(self.__dict__[textlist], edit=True, removeItem=long_name)
                    # Remove weight for source objects
                    if textlist == 'uiSourceList' and long_name in self.uiValues.sourceWeights:
                        del self.uiValues.sourceWeights[long_name]


        #self.__dict__[objlist].printObj()
        
        # Save object lists after any change
        if sp3d_log: print("DEBUG: uiListCallback calling saveObjectLists (mode: %s)" % mode)
        self.uiValues.saveObjectLists(self.sourceList, self.targetList, self.uiSourceList, self.uiTargetList)
        
        self.updateCtx()




    def genericContextCallback(self, *args):
        '''
        Handle the paint/place context button callbacks
        '''
        #print "genericCallback called: " + str(args)

        #delete the setup option UI if it's opened
        if mc.window(spPaint3dSetupID, exists=True):
            mc.deleteUI(spPaint3dSetupID)

        #validate the objects from both lists and raise an error if necessary
        sourcevalid = self.sourceList.validateObjects()
        targetvalid = self.targetList.validateObjects()
        duplicateerror = self.sourceList.hasDuplicate(self.targetList)

        if(not sourcevalid):
            self.errorHandle.raiseError("Source list is empty or object(s) have been deleted. FIX!")
        elif(not targetvalid):
            self.errorHandle.raiseError("Target list is empty or object(s) have been deleted. FIX!")
        elif(duplicateerror):
            self.errorHandle.raiseError("Object(s) can't be in both lists, FIX!")
        else:
            #if we reach here, then there seem to be no errors caught
            #call the appropriate context and set self attributes
            if (args[0] == 'PaintCtx'):
                #creating (or overwritring with) a paint context
                self.errorHandle.raiseError("Engage!! Maximum Paint...")
                self.ctx = spPaint3dContext2025.paintContext(self.uiValues, self.transform, self.sourceList, self.targetList)
                self.ctx.runContext()
            elif (args[0] == 'PlaceCtx'):
                #creating (or overwritring with) a place context
                self.errorHandle.raiseError("Engage!! Maximum Place...")
                self.ctx = spPaint3dContext2025.placeContext(self.uiValues, self.transform, self.sourceList, self.targetList)
                self.ctx.runContext()


    def setupWin(self, uiOptions):
        '''
        Create setup UI
        '''
        self.uiSetupWin = mc.window(spPaint3dSetupID, title=("spPaint3dSetup | " + str(spPaint3dVersion)), width=250, height=450, resizeToFitChildren=True, sizeable=True, titleBar=True, minimizeButton=False, maximizeButton=False, menuBar=False, menuBarVisible=False, toolbox=True)

        #----------------------
        # Top buttons
        #----------------------
        self.uiSetupTopColumn = mc.columnLayout(adjustableColumn=True, columnAttach=('both', 5))
        self.uiSetupTopForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupBtnHelp = mc.button(label='Help', command=lambda * args:self.setupButtonCallback('uiSetupBtnHelp', args))
        self.uiSetupBtnHomepage = mc.button(label='Homepage', command=lambda * args:self.setupButtonCallback('uiSetupBtnHomepage', args))
        self.uiSetupBtnReset = mc.button(label='Reset', command=lambda * args:self.setupButtonCallback('uiSetupBtnReset', args))

        mc.formLayout(self.uiSetupTopForm, edit=True, attachControl=[(self.uiSetupBtnHomepage, 'left', 5, self.uiSetupBtnHelp), (self.uiSetupBtnReset, 'left', 5, self.uiSetupBtnHomepage)])

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # Duplicate Options
        #----------------------
        self.uiSetupDuplicateFrame = mc.frameLayout(label='Duplicate Options', marginHeight=5, marginWidth=20)
        self.uiSetupDuplicateForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupChkInputConn = mc.checkBoxGrp(label='Preserve input connections', changeCommand=lambda * args:self.setupCallback('uiSetupChkInputConn', args), numberOfCheckBoxes=1, width=170)

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # Surface Normals
        #----------------------
        self.uiSetupNormalFrame = mc.frameLayout(label='Surface Normals', marginHeight=5, marginWidth=20)
        self.uiSetupNormalForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupNormalCol = mc.radioCollection()
        self.uiSetupNormalSmooth = mc.radioButton(label='Geometry normal', align='right', onCommand=lambda * args:self.setupCallback('uiSetupNormalCol', True))
        self.uiSetupNormalHard = mc.radioButton(label='Force hard normal', align='right', onCommand=lambda * args:self.setupCallback('uiSetupNormalCol', False))

        mc.formLayout(self.uiSetupNormalForm, edit=True, attachControl=[(self.uiSetupNormalHard, 'top', 5, self.uiSetupNormalSmooth)])

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # Flux control
        #----------------------
        self.uiSetupFluxFrame = mc.frameLayout(label='Flux Control', marginHeight=5, marginWidth=20)
        self.uiSetupFluxForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupFluxCol = mc.radioCollection()
        self.uiSetupFluxTimer = mc.radioButton(label='Timer', align='right', onCommand=lambda * args:self.setupCallback('uiSetupFluxCol', False))
        self.uiSetupFluxDistance = mc.radioButton(label='Distance threshold', align='right', onCommand=lambda * args:self.setupCallback('uiSetupFluxCol', True))

        mc.formLayout(self.uiSetupFluxForm, edit=True, attachControl=[(self.uiSetupFluxDistance, 'top', 5, self.uiSetupFluxTimer)])

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # Hierarchy
        #----------------------
        self.uiSetupHierarchyFrame = mc.frameLayout(label='Hierarchy Management', marginHeight=5, marginWidth=20)
        self.uiSetupHierarchyForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupHierarchyActive = mc.checkBoxGrp(label='Activate objects grouping', changeCommand=lambda * args:self.setupCallback('uiSetupHierarchyActive', args), numberOfCheckBoxes=1)
        self.uiSetupHierarchyCol = mc.radioCollection()
        self.uiSetupHierarchySession = mc.radioButton(label='Single paint session group', align='right', onCommand=lambda * args:self.setupCallback('uiSetupHierarchySession', args))
        self.uiSetupHierarchyStroke = mc.radioButton(label='Stroke sorted group(s)', align='right', onCommand=lambda * args:self.setupCallback('uiSetupHierarchyStroke', args))
        self.uiSetupHierarchySource = mc.radioButton(label='Source sorted group(s)', align='right', onCommand=lambda * args:self.setupCallback('uiSetupHierarchySource', args))

        mc.formLayout(self.uiSetupHierarchyForm, edit=True, attachControl=[(self.uiSetupHierarchySession, 'top', 5, self.uiSetupHierarchyActive), (self.uiSetupHierarchyStroke, 'top', 5, self.uiSetupHierarchySession), (self.uiSetupHierarchySource, 'top', 5, self.uiSetupHierarchyStroke)])
        mc.formLayout(self.uiSetupHierarchyForm, edit=True, attachForm=[(self.uiSetupHierarchySession, 'left', 25), (self.uiSetupHierarchyStroke, 'left', 25), (self.uiSetupHierarchySource, 'left', 25)])

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # Jitter Algorithm
        #----------------------
        self.uiSetupJitterFrame = mc.frameLayout(label='Jitter Algorithm', marginHeight=5, marginWidth=20)
        self.uiSetupJitterForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupJitterAlgorithmMenu = mc.optionMenu(label='Algorithm', changeCommand=lambda * args:self.setupJitterAlgorithmCallback(args))
        mc.menuItem(label='Simple')
        mc.menuItem(label='Re-raycast')
        
        mc.setParent(self.uiSetupTopColumn)
        
        #----------------------
        # Dev feature
        #----------------------
        self.uiSetupDevFrame = mc.frameLayout(label='Advanced Features', marginHeight=5, marginWidth=20)
        self.uiSetupDevForm = mc.formLayout(numberOfDivisions=100)
        self.uiSetupRealTimeRampFX = mc.checkBoxGrp(label='Realtime RampFX', changeCommand=lambda * args:self.setupCallback('uiSetupRealTimeRampFX', args), numberOfCheckBoxes=1)
        self.uiSetupForceVisibility = mc.checkBoxGrp(label='Force visibility', ann='Automatically make duplicated objects visible regardless of source visibility', changeCommand=lambda * args:self.setupCallback('uiSetupForceVisibility', args), numberOfCheckBoxes=1)
        self.uiSetupAllowNegativeScale = mc.checkBoxGrp(label='Allow Negative Scale', ann='Allow scale values to go below zero (enables mirroring/inversion effects)', changeCommand=lambda * args:self.setupCallback('uiSetupAllowNegativeScale', args), numberOfCheckBoxes=1)
        self.uiSetupContinuousTransform = mc.checkBoxGrp(label='Continuous transform', changeCommand=lambda * args:self.setupCallback('uiSetupContinuousTransform', args), numberOfCheckBoxes=1)

        mc.formLayout(self.uiSetupDevForm, edit=True, 
                     attachForm=[(self.uiSetupRealTimeRampFX, 'top', 0), (self.uiSetupRealTimeRampFX, 'left', 0), (self.uiSetupForceVisibility, 'left', 0), (self.uiSetupAllowNegativeScale, 'left', 0), (self.uiSetupContinuousTransform, 'left', 0)],
                     attachControl=[(self.uiSetupForceVisibility, 'top', 5, self.uiSetupRealTimeRampFX), (self.uiSetupAllowNegativeScale, 'top', 5, self.uiSetupForceVisibility), (self.uiSetupContinuousTransform, 'top', 5, self.uiSetupAllowNegativeScale)])

        mc.setParent(self.uiSetupTopColumn)

        #----------------------
        # 
        #----------------------

        self.updateUISetupControls(uiOptions)
        mc.showWindow(self.uiSetupWin)


    def updateUISetupControls(self, ui):
        '''
        Will update the self ui controls with the values stores in the passed instance object
        '''
        if(sp3d_log): print (ui.__dict__)
        mc.checkBoxGrp(self.uiSetupChkInputConn, edit=True, value1=ui.preserveConn)
        mc.checkBoxGrp(self.uiSetupRealTimeRampFX, edit=True, value1=ui.realTimeRampFX)
        mc.checkBoxGrp(self.uiSetupAllowNegativeScale, edit=True, value1=ui.allowNegativeScale)
        mc.checkBoxGrp(self.uiSetupForceVisibility, edit=True, value1=ui.forceVisibility)
        mc.radioButton(self.uiSetupNormalSmooth, edit=True, select=ui.smoothNormal)
        mc.radioButton(self.uiSetupNormalHard, edit=True, select=(not ui.smoothNormal))
        mc.radioButton(self.uiSetupFluxTimer, edit=True, select=(not ui.paintFlux))
        mc.radioButton(self.uiSetupFluxDistance, edit=True, select=ui.paintFlux)

        # Update jitter algorithm option menu
        if ui.jitterAlgorithm == 0:
            mc.optionMenu(self.uiSetupJitterAlgorithmMenu, edit=True, value='Simple')
        elif ui.jitterAlgorithm == 1:
            mc.optionMenu(self.uiSetupJitterAlgorithmMenu, edit=True, value='Re-raycast')

        mc.checkBoxGrp(self.uiSetupContinuousTransform, edit=True, value1=ui.continuousTransform)


        # toggling the proper hierarchy grouping options
        mc.checkBoxGrp(self.uiSetupHierarchyActive, edit=True, value1=ui.hierarchy)
        if(sp3d_log): print ("ui.hierarchy %s" % ui.hierarchy)
        if (ui.hierarchy):
            #toggling radio button enabled
            if(sp3d_log): print ("toggling grouping option ON")
            mc.radioButton(self.uiSetupHierarchySession, edit=True, enable=True)
            mc.radioButton(self.uiSetupHierarchyStroke, edit=True, enable=True)
            mc.radioButton(self.uiSetupHierarchySource, edit=True, enable=True)
        else:
            #toggling radio button disable
            if(sp3d_log): print ("toggling grouping option OFF")
            mc.radioButton(self.uiSetupHierarchySession, edit=True, enable=False)
            mc.radioButton(self.uiSetupHierarchyStroke, edit=True, enable=False)
            mc.radioButton(self.uiSetupHierarchySource, edit=True, enable=False)

        if(ui.group == 0.0):
            mc.radioButton(self.uiSetupHierarchySession, edit=True, select=True)
        elif(ui.group == 1.0):
            mc.radioButton(self.uiSetupHierarchyStroke, edit=True, select=True)
        elif(ui.group == 2.0):
            mc.radioButton(self.uiSetupHierarchySource, edit=True, select=True)

    def resetOptions(self):
        '''
        Will reset to defaults the options
        '''
        #TODO: loop/reset the option
        #TODO: update setup window UI
        #TODO: callback main UI window for update
        #TODO: callback to context if active with new options
        self.uiValues.resetVars()
        self.updateUISetupControls(self.uiValues)
        self.updateUIControls(self.uiValues)
        self.uiTransformReset()
        
        #deleting windowprefs and forcing resize
        if mc.windowPref(spPaint3dSetupID, exists=True): mc.windowPref(spPaint3dSetupID, remove=True)
        if mc.windowPref(spPaint3dGuiID, exists=True): mc.windowPref(spPaint3dGuiID, remove=True)

        if mc.window(spPaint3dGuiID, exists=True):
            #forcing all frame to uncollapse if any
            mc.frameLayout(self.uiSourceFrame, edit=True, collapse=False)
            mc.frameLayout(self.uiTransformFrame, edit=True, collapse=False)
            mc.frameLayout(self.uiTargetFrame, edit=True, collapse=False)
            mc.frameLayout(self.uiPaintFrame, edit=True, collapse=False)
            mc.frameLayout(self.uiPaintMetricsFrame, edit=True, collapse=False)
            self.resizeWindow('winui', spPaint3dGuiID_Height) # force a resize to prevent some weird UI issue on mac


    def setupButtonCallback(self, *args):
        '''
        Manage top buttons commands
        '''
        button = args[0]
        if(button == 'uiSetupBtnHelp'):
            mc.confirmDialog(title=spPaint3dGuiID + ' ' + str(spPaint3dVersion) + ' Help', message='Please refer to the included spPaint3d_ReadMe.html file for detailed help on how to use the script.\n Or use the Homepage button right there.', button='Whatever')
        elif(button == 'uiSetupBtnHomepage'):
            webbrowser.open('http://www.creativecrash.com/maya/downloads/scripts-plugins/utility-external/misc/c/sppaint3d')
        elif(button == 'uiSetupBtnReset'):
            self.resetOptions()


    def setupJitterAlgorithmCallback(self, *args):
        '''
        Callback for jitter algorithm option menu
        '''
        # The args come as a tuple, get the first element which is the selected menu item
        selected = args[0][0]  # Extract the string from the tuple
        
        if selected == 'Simple':
            self.uiValues.jitterAlgorithm = 0
        elif selected == 'Re-raycast':
            self.uiValues.jitterAlgorithm = 1
            
        self.uiValues.commitVars()
        if sp3d_log: print('Jitter algorithm changed to: %s (value: %s)' % (selected, self.uiValues.jitterAlgorithm))

    def setupCallback(self, *args):
        '''
        Manage checkbox and radio buttons
        uiNormalCol
        uiFluxCol
        uiSetupHierarchyActive
        '''
        radiocol = args[0]
        if (sp3d_log): print ('setupCallback control:%s | value: %s' % (args[0], args[1]))
        if(radiocol == 'uiSetupNormalCol'):
            self.uiValues.smoothNormal = args[1]
        elif(radiocol == 'uiSetupFluxCol'):
            self.uiValues.paintFlux = args[1]
        elif(radiocol == 'uiSetupChkInputConn'):
            #Maya callback sends a tuple back for checkbox but seems not a boolean and has to be processed???
            self.uiValues.preserveConn = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        elif(radiocol == 'uiSetupHierarchyActive'):
            self.uiValues.hierarchy = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        elif(radiocol == 'uiSetupRealTimeRampFX'):
            self.uiValues.realTimeRampFX = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        elif(radiocol == 'uiSetupAllowNegativeScale'):
            self.uiValues.allowNegativeScale = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        elif(radiocol == 'uiSetupForceVisibility'):
            self.uiValues.forceVisibility = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        elif(radiocol == 'uiSetupHierarchySession'):
            self.uiValues.group = 0.0
        elif(radiocol == 'uiSetupHierarchyStroke'):
            self.uiValues.group = 1.0
        elif(radiocol == 'uiSetupHierarchySource'):
            self.uiValues.group = 2.0
        elif(radiocol == 'uiSetupContinuousTransform'):
            self.uiValues.continuousTransform = getBoolFromMayaControl(args[1][0], self.mayaVersion)
        else:
            print (args)

        self.uiValues.commitVars()
        self.updateUIControls(self.uiValues)
        self.updateUISetupControls(self.uiValues)
        if(sp3d_log): print ("done updating SetupUI\n")

#-----------------------------------------------------------------------------------
#    UTILITIES
#-----------------------------------------------------------------------------------

def getBoolFromMayaControl(uicontrol, version):
    '''
    return the bool state of the passed uicontrol, return false by default
    Maya returns control state as string pre-2011 and as bool 2011+
    '''
    state = False
    if (version - 2011 >= 0):
        #at least a maya 2011
        state = uicontrol
    else:
        #pre2011, UI controls were returning the state as string and not as a bool prior to 2011
        if(uicontrol == 'true'):
            state = True
    return state


def getMayaVersion():
    '''
    attempt to detect the version of maya and return it as a numerical value.
    '''
    version = mc.about(v=True)
    supportedversion = False
    while not supportedversion:
        try:
            version = int(version[:4])
            supportedversion = True
        except ValueError:
            result = mc.promptDialog(title='Enter Maya version', message='Couldn\'t determine the version of Maya\n, please enter the 4 digits of the maya version you are using (ie: 2011)', button=['OK', 'Cancel & Quit'], defaultButton='OK', cancelButton='Cancel & Quit', dismissString='Cancel & Quit')
            if result == 'OK':
                version = mc.promptDialog(query=True, text=True)
            else:
                sys.exit()
    if (version <= 2010): mc.confirmDialog(title='Maya version alert', message='This version of the script was updated for Maya 2011 and above.\nThere will be unexpected stuff happening with older versions, or not...')
    return version


def getDAGPath(node, depth=False):
    '''
    Return the DAG path of the node argument (node must be a transform, if not, will attempt to locate its immediate parent and make sure it's a transform and will proceed from there)
    Return the extended DAG path to the node's shape when depth=True
    Return None if the node doesn't have any shape children, or more than one children shape.
    '''
    dag = None
    nodetype = mc.objectType(node)

    if(nodetype != 'transform'):
        #node is not a transform, will proceed upstream to its immediate parent and will verify if the parent is a transform
        tempdag = mc.listRelatives(node, parent=True)
        if(tempdag):
            #node has a parent
            if(len(tempdag) == 1):
                #node only has 1 parent, will proceed from there and see if it's a transform with a shape' child
                node = tempdag[0]
                nodetype = mc.objectType(node)

    if(nodetype == 'transform'):
        #node is a transform, making sure it has only one children of shape type
        childlist = mc.listRelatives(node, children=True, shapes=True)
        if(childlist):
            if(len(childlist) == 1):
                #there's only 1 shape below the transform
                if(depth): dag = mc.listRelatives(node, fullPath=True, shapes=True)
                else: dag = mc.listRelatives(node, path=True, shapes=True)

    if(dag):
        return dag[0]
    else:
        return dag


def main():
    #Main function to create and display the spPaint3d GUI
    try:
        # Create the main window
        spPaint3dWin2025()
        print("spPaint3d 2025 - GUI successfully loaded")
        return True
    except Exception as e:
        print("Error loading spPaint3d GUI: " + str(e))
        return False


# Only execute when script is run directly, not when imported
if __name__ == "__main__":
    main()