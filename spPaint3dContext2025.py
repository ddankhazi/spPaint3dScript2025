#-----------------------------------------------------------------
#    SCRIPT           spPaint3dContext2025.py
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

#used for maya versions using pre-2.6 python engine
from __future__ import with_statement
###################################################

import maya.cmds as mc

import maya.OpenMaya as om
import maya.OpenMayaUI as omui
import math as math
import sys

spPaint3dContextID = "spPaint3dContext2025"
spPaint3dTempGroupID = "spPaint3dTempGroup2025"

#unit conversion dictionnary relative to 1 cm (default unit system)
sp3dUnit = {
                    "mm": 10,
                    "cm": 1,
                    "m": 0.01,
                    "in": 0.393701,
                    "ft": 0.0328084,
                    "yd": 0.0109361,}

sp3d_dbgfile = "C:\\sp3ddbg_log.txt"
sp3d_dbg = False #debug flag to log to file
sp3d_log = False #debug flag to log to script editor log
sp3d_place = False #debug flag for place context
sp3d_ramp = False #debug flag for rampFX
sp3d_MFn = False #debug flag for MFn stuff

class point (object):
    '''
    define an object of 3 attributes used for various purposes
    '''
    def __init__(self, x, y, z):
        '''
        initialise object attributes
        '''
        self.x = x
        self.y = y
        self.z = z

    def asMPoint(self):
        '''
        return point as MPoint()
        '''
        return om.MPoint(self.x,self.y,self.z)

    def asMFPoint(self):
        '''
        return point as MFloatPoint()
        '''
        return om.MFloatPoint(self.x,self.y,self.z)

    def asMVector(self):
        '''
        return point as MVector()
        '''
        return om.MVector(self.x,self.y,self.z)

    def asMFVector(self):
        '''
        return point as MFloatVector()
        '''
        return om.MFloatVector(self.x,self.y,self.z)



class intersectionPoint (object):
    '''
    define an intersection point
    '''
    def __init__(self, hitPoint, hitFace, hitTriangle, dagMesh):
        '''
        initial setup
        '''
        self.valid = None        #bool to validate iteration later on
        self.hitPoint = hitPoint     #point.position tuple
        self.hitFace = hitFace         #face number of the intersection
        self.hitTriangle = hitTriangle    #triangle number in the above face
        self.dagMeshTargetSurface = dagMesh        #MDagPath where the intersection occured (used to avoid having to compute all normals on soon-to-be discarded intersections
        self.timestamp = None     #used to track the creation of an object at that intersectionPoint (later used in the strokePointList class)
        self.dagMeshSourceObject = None     #used to store the DAG path of the created geometry if it's actually a valid intersection
        self.generatedDAG = None    #used to store the DAG path of the created object
        self.initialScale = [1,1,1] #used to store the self.generatedDAG initial scale

    def getHitNormal(self, smooth=False):
        '''
        return the normal (MVector) at the self.hitPoint, compute the normal differently according to the smooth boolean argument
        '''
        if (smooth):
            #getting the intersection normal from the MFnMesh method
            normal = om.MVector()
            fnMesh = om.MFnMesh( self.dagMeshTargetSurface )
            fnMesh.getClosestNormal(self.hitPoint.asMPoint(), normal, om.MSpace.kWorld, None)

            return normal
        else:
            #compute hard normal (decal mode)
            hitFacept =om.MScriptUtil()
            om.MScriptUtil().setInt(hitFacept.asIntPtr(),self.hitFace)
            itMesh = om.MItMeshPolygon(self.dagMeshTargetSurface)
            itMesh.setIndex(self.hitFace, hitFacept.asIntPtr())
            triVertsArray = om.MPointArray()
            triIndexArray = om.MIntArray()
            itMesh.getTriangle(self.hitTriangle, triVertsArray, triIndexArray, om.MSpace.kWorld)

            return self.getCrossProduct(triVertsArray[0],triVertsArray[1],triVertsArray[2])

    def convertUnit(self, currentUnit):
        '''
        will convert the stored intersection internal coordinates into the current unit of the scene
        '''
        if(currentUnit!='cm'):
            self.hitPoint.x = float(mc.convertUnit(self.hitPoint.x, fromUnit='cm', toUnit=currentUnit))
            self.hitPoint.y = float(mc.convertUnit(self.hitPoint.y, fromUnit='cm', toUnit=currentUnit))
            self.hitPoint.z = float(mc.convertUnit(self.hitPoint.z, fromUnit='cm', toUnit=currentUnit))

    def getCrossProduct(self, p1, p2, p3):
        '''
        return the cross product from the 3 points
        '''
        vectA = om.MVector( (p2.x-p1.x), (p2.y-p1.y), (p2.z-p1.z) )
        vectB = om.MVector( (p3.x-p1.x), (p3.y-p1.y), (p3.z-p1.z) )
        vectA.normalize()
        vectB.normalize()
        return self.doCrossProduct(vectA, vectB)


    def doCrossProduct(self, v1, v2):
        '''
        compute the cross product vectors
        '''
        vectNorm = om.MVector( ((v1.y*v2.z) - (v1.z*v2.y)) , ((v1.z*v2.x) - (v1.x*v2.z)), ((v1.x*v2.y) - (v1.y*v2.x)) )
        vectNorm.normalize()
        return vectNorm

    def startTimer(self):
        '''
        start the timerX for the current object
        '''
        self.timestamp = mc.timerX()

    def updateDAGSourceObject(self, dagstring):
        '''
        update self.dagMeshSourceObject with the dagstring argument
        '''
        self.dagMeshSourceObject = dagstring

    def createdObjectDAG(self, dagstring):
        '''
        update the self.generatedDAG with the dagstring argument
        '''
        self.generatedDAG = dagstring

    def setInitialScale(self):
        '''
        Set initial scale to the intersected point dag object created
        '''
        self.initialScale=mc.xform(self.generatedDAG, query=True, scale=True, r=True)
        
    def isValid(self,confirm=None):
        '''
        put the valid flag to the passed value. return the current flag state
        '''
        if confirm != None: self.valid=confirm
        return self.valid




class intersectionList (object):
    '''
    define list of intersection points
    '''
    def __init__(self, ipoint=None):
        '''
        initial setup
        input: point object, (optional point object)
        '''
        self.intersectionList = []
        if (ipoint): self.addPoint(ipoint)
        if(sp3d_log): print ("creating a new intersectionList (empty? %s)" % self.intersectionList)

    def addPoint(self, ipoint):
        '''
        add a point to the list
        '''
        self.intersectionList.append(ipoint)
        if(sp3d_log):
            print ("adding a new intersection to intersectionList (length of list: %i)" % len(self.intersectionList))
        #    self.printList()

    def getLength(self):
        '''
        return the length of the sel.intersectionList
        '''
        return len(self.intersectionList)
    
    def getClosest(self, sortorigin):
        '''
        will parse the list to return the closest intersectionPoint to the sortorigin argument
        return None if the list is empty
        '''
        length = len(self.intersectionList)
        closestintersection = None
        closestdistance = None

        if (length==0): return None
        elif (length==1): return self.intersectionList[0]
        else:
            #list is at least 2 intersections
            for intersection in self.intersectionList:
                if not closestintersection:
                    #first intersection considered
                    closestintersection = intersection
                    closestdistance = getDistanceBetween(intersection.hitPoint, sortorigin)
                else:
                    #compare distances
                    newdistance = getDistanceBetween(intersection.hitPoint, sortorigin)
                    if ( newdistance < closestdistance):
                        #new closest
                        closestintersection = intersection
                        closestdistance = newdistance
            #at this point there must be a closesintersetcion
            return closestintersection

    def printList(self):
        '''
        debug: print the dag of all objects in the list
        '''
        for obj in self.intersectionList:
            print ("object created: %s (using source: %s)" % (obj.generatedDAG, obj.dagMeshSourceObject))


class modifierManager (object):
    '''
    Wrapper to manage the modifier keypress / release used in the place context
    '''
    modifierMask = {     'shift' : 1,
                        'ctrl' : 4,
                        'alt' : 8}

    def __init__(self):
        '''
        setup various variables used
        '''
        self.ctrlReleased = True
        self.shiftReleased = True
        self.altReleased = True


    def resetCtrl(self):
        '''
        reset ctrl back to default settings, usually after the key press was acted upon
        '''
        pass


    def getState(self):
        '''
        return 3 booleans for ctrl / shift / alt state keypress event
        '''
        ctrl = shift = alt = False
        modifiers = mc.getModifiers()

        # SHIFT EVENT
        if (modifiers & 1) > 0 :
            if (self.shiftReleased):
                # shift was released in the previous iteration, this is a keypress
                self.shiftReleased = False
                shift = True
        else:
            # shift is not currently pressed, reseting the tracking self variable to released state
            self.shiftReleased = True

        # CTRL EVENT
        if (modifiers & 4) > 0 :
            if (self.ctrlReleased):
                # ctrl was released in the previous iteration, this is a keypress
                self.ctrlReleased = False
                ctrl = True
        else:
            # ctrl is not currently pressed, reseting the tracking self variable to released state
            self.ctrlReleased = True

        # ALT EVENT
        if (modifiers & 8) > 0 :
            if (self.altReleased):
                # alt was released in the previous iteration, this is a keypress
                self.altReleased = False
                alt = True
        else:
            # alt is not currently pressed, reseting the tracking self variable to released state
            self.altReleased = True

        return ctrl, shift, alt

    def isPressed(self, modifier):
        '''
        returns True if the modifier is currently pressed
        '''
        bitmask = mc.getModifiers() & self.modifierMask[modifier]
        if bitmask > 0 : return True
        else: return False




class placeCursor (object):
    '''
    define a cursor object for use with placeContext
    '''
    def __init__(self, sourcedag=None, cursordag=None):
        '''
        initialize variables
        '''
        self.position=None
        self.rotation=None
        self.rotationIncrement=None
        self.initialScale=[1,1,1]
        self.cursorAlign=None
        if(sourcedag and cursordag):
            self.setCursorDAG(sourcedag, cursordag)

    def setCursorDAG(self, sourcedag, cursordag, deleteprevious=False):
        '''
        update the cursor dag
        '''
        self.sourceDAG = sourcedag
        self.sourceDAGPos = getPosition(sourcedag)
        if (deleteprevious):
            if(mc.objExists(self.cursorDAG)):
                #deleting the previous cursor object and its parent group if it's empty
                parentgroup = mc.listRelatives(self.cursorDAG, parent=True)
                mc.delete(self.cursorDAG)
                if (not mc.listRelatives(parentgroup)): mc.delete(parentgroup)
        self.cursorDAG = cursordag
        self.initialScale=mc.xform(self.cursorDAG, query=True, scale=True, r=True)

    def setCursorTransform(self, rotate, scale):
        '''
        store transform tuples for rotate and scale of the cursor
        '''
        self.rotate = rotate
        self.scale = scale

    def move(self, position=None, rotation=None):
        '''
        move the cursor object to position of point type
        '''
        if (not position):
            #reseting current position to previously stored position if any
            if (self.position):
                moveTo(self.cursorDAG, self.position)
                if (rotation):
                    mc.rotate(self.rotationIncrement[0], self.rotationIncrement[1], self.rotationIncrement[2], self.cursorDAG, os=True, r=True, rotateXYZ=True)
        else:
            self.position = position
            moveTo(self.cursorDAG, position)
            if (rotation):
                mc.rotate(self.rotationIncrement[0], self.rotationIncrement[1], self.rotationIncrement[2], self.cursorDAG, os=True, r=True, rotateXYZ=True)

    def rotateCursor(self, increment):
        '''
        rotate the cursor object
        '''
        if self.rotationIncrement:
            self.rotationIncrement = [(self.rotationIncrement[0]+increment[0]),(self.rotationIncrement[1]+increment[1]),(self.rotationIncrement[2]+increment[2])]
        else: self.rotationIncrement=increment
        
        #rotating the cursor from the rotate increment
        mc.rotate(increment[0], increment[1], increment[2], self.cursorDAG, os=True, r=True, rotateXYZ=True)

    def align(self, rx=None, ry=None, rz=None):
        '''
        orient the cursor along the supplied rotation angles
        '''
        if ((rx!=None) and (ry!=None) and (rz!=None)):
            self.cursorAlign = rx, ry, rz
            mc.xform(self.cursorDAG, ro=(rx, ry, rz) )
        else:
            #realigning cursor with previously stored rotate tuple if it exists
            if(self.cursorAlign):
                rx, ry, rz = self.cursorAlign
                mc.xform(self.cursorDAG, ro=(rx, ry, rz) )


    def transform(self, rotate=False, scale=False):
        '''
        transform the cursor with self transform scale and rotate
        '''
        if (rotate):
            mc.rotate(self.rotate[0], self.rotate[1], self.rotate[2], self.cursorDAG, os=True, r=True, rotateXYZ=True)
        if (scale):
            mc.scale(self.scale[0], self.scale[1], self.scale[2], self.cursorDAG, relative=False)

    def asTemplate(self, mode=True):
        '''
        set cursor object in or out of template mode
        '''
        #TODO: Check if cursorDAG is a transform
        if (mode):
            #set to template
            mc.setAttr(self.cursorDAG+'.overrideEnabled', 1)
            mc.setAttr(self.cursorDAG+'.overrideDisplayType', 1)
        else:
            #set to normal
            mc.setAttr(self.cursorDAG+'.overrideEnabled', 0)
            mc.setAttr(self.cursorDAG+'.overrideDisplayType', 0)

class placeContext (object):
    '''
    define placeContext
    '''
    def _is_true(self, value):
        """Robust truthiness for UI values (accepts bool/int/str)."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return False
    def _clean_tempgroup_if_empty(self):
        """Delete any empty tempgroup(s) that match the base prefix."""
        base = spPaint3dTempGroupID + "*"
        for tg in (mc.ls(base, type='transform') or []):
            kids = mc.listRelatives(tg, children=True) or []
            if not kids:
                mc.delete(tg)

    def _sweep_empty_tempgroups(self):
        """Proactively sweep and remove any stale empty temp groups from prior strokes."""
        self._clean_tempgroup_if_empty()

    def __init__(self, uioptions, transformoptions, sourcelist, targetlist):
        # create the tool context
        if (mc.draggerContext(spPaint3dContextID, exists=True)):
            mc.deleteUI(spPaint3dContextID)
        mc.draggerContext(
            spPaint3dContextID,
            pressCommand=self.onPress,
            prePressCommand=self.onBeforePress,
            dragCommand=self.onDrag,
            holdCommand=self.onHold,
            releaseCommand=self.onRelease,
            name=spPaint3dContextID,
            cursor='crossHair',
            undoMode='step'
        )

        # create context local options
        self.runtimeUpdate(uioptions, transformoptions, sourcelist, targetlist)

        # initialise world up vector
        if (mc.upAxis(q=True, axis=True)) == "y":
            self.worldUp = om.MVector(0, 1, 0)
        elif (mc.upAxis(q=True, axis=True)) == "z":
            self.worldUp = om.MVector(0, 0, 1)

        # fetch current scene unit
        self.unit = mc.currentUnit(query=True, linear=True)

        self.reentrance = 0
        self.mState = modifierManager()

        # important: default tempgroup handle
        self.tempgroup = None



    def runContext(self):
        '''
        set maya tool to the context
        '''
        if (mc.draggerContext(spPaint3dContextID, exists=True)): mc.setToolTo(spPaint3dContextID)

    def fetchCursorObject(self):
        """
        Gather necessary data and generate a new cursor object.
        Returns (sourceDAG, cursorDAG).
        """
        # pick source
        if self.uiValues.random:
            # Use weighted selection if weights are available
            useWeights = len(self.uiValues.sourceWeights) > 0
            sourceDAG = self.sourceList.getRandom(weighted=useWeights, sourceWeights=self.uiValues.sourceWeights)
        else:
            sourceDAG = self.sourceList.getNext()

        # ensure we work with a transform
        if mc.nodeType(sourceDAG) != 'transform':
            temp = mc.listRelatives(sourceDAG, parent=True)
            if temp:
                sourceDAG = temp[0]

        # create instance or duplicate
        if self.uiValues.instance:
            newObjectDAG = mc.instance(sourceDAG)
        else:
            newObjectDAG = mc.duplicate(sourceDAG, ic=self.uiValues.preserveConn)

        # Always convert to long names (namespace-safe)
        newObjectDAG = [mc.ls(obj, long=True)[0] for obj in newObjectDAG]

        # When duplicating groups, Maya returns [group, child1, child2, ...] 
        # We only need the top-level group/object (silently handle without warnings)
        if len(newObjectDAG) > 1:
            if mc.nodeType(newObjectDAG[0]) == 'transform':
                newObjectDAG = [newObjectDAG[0]]
            else:
                fullPaths = [mc.ls(dag, long=True)[0] for dag in newObjectDAG]
                topLevelNodes = []
                for i, dag in enumerate(fullPaths):
                    parents = mc.listRelatives(dag, parent=True, fullPath=True) or []
                    isTopLevel = True
                    for parent in parents:
                        if parent in fullPaths:
                            isTopLevel = False
                            break
                    if isTopLevel:
                        topLevelNodes.append(newObjectDAG[i])
                if topLevelNodes:
                    newObjectDAG = [topLevelNodes[0]]
                else:
                    newObjectDAG = [newObjectDAG[0]]

        # ensure created cursor object is visible if forceVisibility option is enabled
        if self.uiValues.forceVisibility:
            mc.setAttr(newObjectDAG[0] + '.visibility', 1)

        # tempgroup only when grouping is enabled
        if self._is_true(self.uiValues.hierarchy):
            self.tempgroup = mc.group(empty=True, name=spPaint3dTempGroupID)
            # Always use long names for parenting
            parented = mc.parent(newObjectDAG[0], self.tempgroup, relative=True)
            parented = [mc.ls(obj, long=True)[0] for obj in parented]
            cursorDagOut = parented[0]
        else:
            self.tempgroup = None
            cursorDagOut = newObjectDAG[0]

        return sourceDAG, cursorDagOut


    def fetchCursorTransform(self):
        '''
        compute transform data for cursor object and return the tuple for rotate and scale
        '''
        # getting the proper transform tuples
        if (self.uiValues.transformRotate):
            cursorRotate = self.transform.getRandomRotate(self.uiValues)
        else:
            #transform rotate off
            cursorRotate = (0,0,0)

        if (self.uiValues.transformScale):
            tempCursorScale = self.transform.getRandomScale(self.uiValues.transformScaleUniform)
            cursorScale = [tempCursorScale[0]*self.cursor.initialScale[0],tempCursorScale[1]*self.cursor.initialScale[1],tempCursorScale[2]*self.cursor.initialScale[2]] 
        else:
            #transform scale off
            cursorScale = (1,1,1)

        return cursorRotate, cursorScale

    def ctrlEvent(self):
        '''
        ctrl event stuff
        '''
        #fetching a new cursor
        newSourceDAG, newCursorDAG = self.fetchCursorObject()
        self.cursor.setCursorDAG(newSourceDAG,newCursorDAG,True) #flagging to delete previous cursor
        
        # Recalculate transforms with the new object's scale
        cursorRotate, cursorScale = self.fetchCursorTransform()
        self.cursor.setCursorTransform(cursorRotate, cursorScale)
        
        if(self.uiValues.align):
            self.cursor.align()
        self.cursor.move(None, self.cursor.rotationIncrement) #defaulting without parameters to position the new cursor to the previously stored position
        self.cursor.transform(self.uiValues.transformRotate, self.uiValues.transformScale)
        if (self.uiValues.upOffset != 0):
           offsetArray = [self.uiValues.upOffset*self.worldUp.x,self.uiValues.upOffset*self.worldUp.y,self.uiValues.upOffset*self.worldUp.z]
           mc.move(offsetArray[0],offsetArray[1],offsetArray[2],self.cursor.cursorDAG,relative=True) 

    def shiftEvent(self):
        '''
        shift event stuff (rotate on upvector)
        '''
        if self.uiValues.rotateIncrementSnap:
            # Generate new snapped rotation values (like paint mode)
            newRotation = self.transform.getRandomRotate(self.uiValues)
            
            # Reset cursor rotation first, then set absolute rotation
            mc.xform(self.cursor.cursorDAG, rotation=(0, 0, 0), worldSpace=True)
            mc.xform(self.cursor.cursorDAG, rotation=newRotation, worldSpace=True)
            
            # Also update the cursor's internal rotation tracking
            self.cursor.rotationIncrement = newRotation
        else:
            # Original increment mode: add increment to current rotation
            rotateArray = [self.worldUp.x*self.uiValues.placeRotate, self.worldUp.y*self.uiValues.placeRotate, self.worldUp.z*self.uiValues.placeRotate]
            self.cursor.rotateCursor(rotateArray)
            
        if sp3d_log: print (self.cursor.rotationIncrement)


    def onBeforePress(self):
        """
        prePress event to setup the temp data for the cursor object
        """
        # pre-stroke hygiene: always sweep stale empty tempgroups, regardless of current grouping
        self._sweep_empty_tempgroups()
        self.tempgroup = None

        sourceDAG, cursorDAG = self.fetchCursorObject()
        self.cursor = placeCursor(sourceDAG, cursorDAG)

        cursorRotate, cursorScale = self.fetchCursorTransform()
        self.cursor.setCursorTransform(cursorRotate, cursorScale)
        self.cursor.transform(self.uiValues.transformRotate, self.uiValues.transformScale)
        # self.cursor.asTemplate()  # known issue with hierarchies

    def onPress(self):
        '''
        on mouse press initial event
        '''
        pressPosition = mc.draggerContext(spPaint3dContextID, query=True, anchorPoint=True)

        #initializing / reseting the rotation increment if we are re-entering place
        self.cursor.rotationIncrement = 0
        
        ctrl, shift, alt = self.mState.getState()

        worldPos, worldDir = getViewportClick(pressPosition[0],pressPosition[1])

        intersected = targetSurfaceLoopIntersect(self.targetList, worldPos, worldDir)
        if(intersected):
            #there was a usable intersection found
            #first checking and converting units if necessary
            intersected.convertUnit(self.unit)
            #now moving the cursor
            self.cursor.move(intersected.hitPoint)
            if(self.uiValues.align):
                rx, ry, rz = getEulerRotationQuaternion(self.worldUp, intersected.getHitNormal(self.uiValues.smoothNormal))
                self.cursor.align(rx,ry,rz)

            #retransforming the cursor rotation if necessary
            self.cursor.transform(self.uiValues.transformRotate)

            if (self.uiValues.upOffset != 0):
               offsetArray = [self.uiValues.upOffset*self.worldUp.x,self.uiValues.upOffset*self.worldUp.y,self.uiValues.upOffset*self.worldUp.z]
               mc.move(offsetArray[0],offsetArray[1],offsetArray[2],self.cursor.cursorDAG,relative=True) 
            
            # Handle modifier keys immediately on press
            if(ctrl):
                self.ctrlEvent()
            if(shift):
                self.shiftEvent()

        else:
            pass
            #no intersection found
            #TODO
            #moving cursor to worldPos and aligning to worldDir

        #forcing a viewport redraw
        forceRefresh()


    def onDrag(self):
        '''
        on mouse drag event
        '''
        if self.reentrance==1: return
        self.reentrance=1

        dragPosition = mc.draggerContext(spPaint3dContextID, query=True, dragPoint=True)

        worldPos, worldDir = getViewportClick(dragPosition[0],dragPosition[1])

        ctrl, shift, alt = self.mState.getState()
        #
        #TODO scale and rotate depending on mouse drag direction
        #
        intersected = targetSurfaceLoopIntersect(self.targetList, worldPos, worldDir)
        if(intersected):
            #there was a usable intersection found
            #first checking and converting units if necessary
            intersected.convertUnit(self.unit)
            #now moving the cursor
            if(self.uiValues.align):
                rx, ry, rz = getEulerRotationQuaternion(self.worldUp, intersected.getHitNormal(self.uiValues.smoothNormal))
                self.cursor.align(rx,ry,rz)
            self.cursor.move(intersected.hitPoint, self.cursor.rotationIncrement)

            
            if self.uiValues.transformRotate or self.uiValues.transformScale:
                #retransforming the cursor rotation if necessary
                self.cursor.transform(self.uiValues.transformRotate)

                if self.uiValues.continuousTransform:
                    cursorRotate, cursorScale = self.fetchCursorTransform()
                    self.cursor.setCursorTransform(cursorRotate, cursorScale)
                    self.cursor.transform(self.uiValues.transformRotate, self.uiValues.transformScale)

            if (self.uiValues.upOffset != 0):
               offsetArray = [self.uiValues.upOffset*self.worldUp.x,self.uiValues.upOffset*self.worldUp.y,self.uiValues.upOffset*self.worldUp.z]
               mc.move(offsetArray[0],offsetArray[1],offsetArray[2],self.cursor.cursorDAG,relative=True) 

        else:
            pass
            #no intersection found
            #TODO
            #moving cursor to worldPos and aligning to worldDir

        if(ctrl):
            self.ctrlEvent()
        if(shift):
            self.shiftEvent()
       
        forceRefresh()
        self.reentrance=0

    def onHold(self):
        '''
        on mouse hold event
        '''
        if self.reentrance==1: return
        self.reentrance=1

        dragPosition = mc.draggerContext(spPaint3dContextID, query=True, dragPoint=True)

        ctrl, shift, alt = self.mState.getState()

        if(ctrl):
            self.ctrlEvent()
        if(shift):
            self.shiftEvent()

        forceRefresh()

        if sp3d_log:
            message = 'key press detected: '
            if (ctrl): message += 'ctrl pressed... '
            if (shift): message += 'shift pressed... '
            if (alt): message += 'alt pressed... '
            print (message)

        self.reentrance=0


    def onRelease(self):
        """
        on mouse release event: CLEANUP
        """
        # grouping
        if self._is_true(self.uiValues.hierarchy):
            g = int(self.uiValues.group)
            if g == 0:
                # single group
                groupName = self.uiValues.getGroupID()
                if not mc.objExists(groupName):
                    groupName = mc.group(empty=True, name=groupName)
                mc.parent(self.cursor.cursorDAG, groupName, relative=True)

            elif g == 1:
                # stroke group
                groupName = mc.group(empty=True, name='spPaint3dStrokeOutput')
                mc.parent(self.cursor.cursorDAG, groupName, relative=True)

            elif g == 2:
                # source group
                shapeParent = mc.listRelatives(self.cursor.sourceDAG, parent=True)
                parentName = shapeParent[0] if shapeParent else self.cursor.sourceDAG
                groupName = 'spPaint3dOutput_' + parentName
                if not mc.objExists(groupName):
                    groupName = mc.group(name=groupName, empty=True)
                mc.parent(self.cursor.cursorDAG, groupName, relative=True)

        # primary cleanup: delete this stroke's tempgroup if exists and is empty
        if getattr(self, "tempgroup", None) and mc.objExists(self.tempgroup):
            kids = mc.listRelatives(self.tempgroup, children=True) or []
            if not kids:
                mc.delete(self.tempgroup)

        # secondary cleanup by NAME: remove any stale empty tempgroup left from earlier strokes
        self._clean_tempgroup_if_empty()


    def runtimeUpdate(self, uioptions, transformoptions, sourcelist, targetlist):
        '''
        entry method used from GUI to pass changes in the UI options through self.ctx.runtimeUpdate(...)
        '''
        self.uiValues = uioptions
        self.transform = transformoptions
        self.sourceList = sourcelist
        self.targetList = targetlist

class paintContext(object):
    '''
    define paintContext
    '''
    def __init__(self, uioptions, transformoptions, sourcelist, targetlist):
        '''
        initial setup
        '''
        # create the tool context
        if (mc.draggerContext(spPaint3dContextID, exists=True)):
            mc.deleteUI(spPaint3dContextID)
        mc.draggerContext(
            spPaint3dContextID,
            pressCommand=self.onPress,
            dragCommand=self.onDrag,
            releaseCommand=self.onRelease,
            name=spPaint3dContextID,
            cursor='crossHair',
            undoMode='step'
        )

        # context local options
        self.runtimeUpdate(uioptions, transformoptions, sourcelist, targetlist)

        # debug purpose
        self.reentrance = 0

        # initialise world up vector
        axis = mc.upAxis(q=True, axis=True)
        if axis == "y":
            self.worldUp = om.MVector(0, 1, 0)
        elif axis == "z":
            self.worldUp = om.MVector(0, 0, 1)
        else:
            mc.confirmDialog(
                title='Weird stuff happening',
                message='Not getting any proper info on what the current up vector is. Quitting...'
            )
            sys.exit()

        # fetch current scene unit
        self.unit = mc.currentUnit(query=True, linear=True)

        # tempgroup handle (lazy-created only when actually painting with hierarchy)
        self.tempgroup = None

    def runContext(self):
        '''
        set maya tool to the context
        '''
        if (mc.draggerContext(spPaint3dContextID, exists=True)):
            mc.setToolTo(spPaint3dContextID)

    def onPress(self):
        '''
        on mouse press initial event
        '''
        if sp3d_dbg:
            logDebugInfo('entered paintContext onPress')

        # initialise the intersection list that will contain all the created objects within the same stroke
        self.strokeIntersectionList = intersectionList()

        # DO NOT create tempgroup here (avoid leftover in Place mode)
        self.tempgroup = None

        pressPosition = mc.draggerContext(spPaint3dContextID, query=True, anchorPoint=True)
        worldPos, worldDir = getViewportClick(pressPosition[0], pressPosition[1])
        intersected = targetSurfaceLoopIntersect(self.targetList, worldPos, worldDir)

        if intersected:
            # usable intersection found
            intersected.convertUnit(self.unit)
            intersected.isValid(True)
            if sp3d_dbg:
                logDebugInfo('found intersected')
            if sp3d_log:
                print('intersection at X: %f | Y: %f | Z: %f' % (
                    intersected.hitPoint.x, intersected.hitPoint.y, intersected.hitPoint.z))

            if not self.uiValues.paintFlux:
                # paintFlux set on timer
                intersected.startTimer()

            # choose source
            if self.uiValues.random:
                useWeights = len(self.uiValues.sourceWeights) > 0
                intersected.dagMeshSourceObject = self.sourceList.getRandom(weighted=useWeights, sourceWeights=self.uiValues.sourceWeights)
            else:
                intersected.dagMeshSourceObject = self.sourceList.getNext()
            if sp3d_dbg:
                logDebugInfo('got the dag for the source object to use')

            # create object
            if sp3d_dbg:
                logDebugInfo('creating object from the dag')
            intersected.createdObjectDAG(self.createObject(intersected))
            intersected.setInitialScale()
            if sp3d_dbg:
                logDebugInfo('finished creating object from the dag, appending to intersection list')
            self.strokeIntersectionList.addPoint(intersected)

            # optional jitter
            if self.uiValues.jitter:
                if self.uiValues.jitterAlgorithm == 1:  # Re-raycast
                    applyJitterWithReRaycast(intersected, self.uiValues, self.transform, self.targetList, self.worldUp)
                else:  # Simple (default)
                    u = self.transform.getRandomJitter('uJitter')
                    v = self.transform.getRandomJitter('vJitter')
                    yOffset = math.fabs(self.worldUp.y - 1) * v
                    zOffset = math.fabs(self.worldUp.z - 1) * v
                    mc.move(u, yOffset, zOffset, intersected.generatedDAG, relative=True)

        if sp3d_dbg:
            logDebugInfo('finished paintContext onPress')
        forceRefresh()

    def onDrag(self):
        '''
        on mouse drag event
        '''
        #print("onDrag: hierarchy =", self.uiValues.hierarchy)
        # reentrance guard
        if self.reentrance == 0:
            self.reentrance = 1
        else:
            return

        if sp3d_dbg:
            logDebugInfo('entered paintContext onDrag')

        # Lazy-create tempgroup only if actually painting AND hierarchy is enabled
        if self.uiValues.hierarchy and not self.tempgroup:
            if not mc.objExists(spPaint3dTempGroupID):
                self.tempgroup = mc.group(empty=True, name=spPaint3dTempGroupID)
            else:
                self.tempgroup = spPaint3dTempGroupID

        dragPosition = mc.draggerContext(spPaint3dContextID, query=True, dragPoint=True)
        worldPos, worldDir = getViewportClick(dragPosition[0], dragPosition[1])
        intersected = targetSurfaceLoopIntersect(self.targetList, worldPos, worldDir)

        if intersected:
            # check coherence with paintFlux settings
            intersected.convertUnit(self.unit)

            if len(self.strokeIntersectionList.intersectionList) == 0:
                # no intersection during onPress
                if sp3d_log:
                    print('intersection at X: %f | Y: %f | Z: %f' % (
                        intersected.hitPoint.x, intersected.hitPoint.y, intersected.hitPoint.z))
                if not self.uiValues.paintFlux:
                    intersected.startTimer()
            else:
                # there was a previous intersection
                if self.uiValues.paintFlux:
                    # distance-based placement
                    distanceToPrevious = getDistanceBetween(
                        self.strokeIntersectionList.intersectionList[-1].hitPoint,
                        intersected.hitPoint
                    )
                    correctedPaintDistance = self.uiValues.paintDistance
                    if sp3d_log:
                        print('intersection at X: %f | Y: %f | Z: %f |||| distance from previous: %f '
                              '(x: %f | y: %f | z: %f)(threshold: %f)(length of list: %i)' % (
                                  intersected.hitPoint.x, intersected.hitPoint.y, intersected.hitPoint.z,
                                  distanceToPrevious,
                                  self.strokeIntersectionList.intersectionList[-1].hitPoint.x,
                                  self.strokeIntersectionList.intersectionList[-1].hitPoint.y,
                                  self.strokeIntersectionList.intersectionList[-1].hitPoint.z,
                                  correctedPaintDistance,
                                  len(self.strokeIntersectionList.intersectionList)))
                    if distanceToPrevious < correctedPaintDistance:
                        intersected.isValid(False)
                    else:
                        intersected.isValid(True)
                else:
                    # timer-based placement
                    if mc.timerX(startTime=self.strokeIntersectionList.intersectionList[-1].timestamp) < self.uiValues.paintTimer:
                        intersected.isValid(False)
                    else:
                        intersected.isValid(True)
                        intersected.startTimer()

            if intersected.isValid():
                if sp3d_log:
                    print("valid intersection, creating object")

                # choose source
                if self.uiValues.random:
                    useWeights = len(self.uiValues.sourceWeights) > 0
                    intersected.updateDAGSourceObject(self.sourceList.getRandom(weighted=useWeights, sourceWeights=self.uiValues.sourceWeights))
                else:
                    intersected.updateDAGSourceObject(self.sourceList.getNext())

                # optional jitter BEFORE object creation
                if self.uiValues.jitter:
                    if self.uiValues.jitterAlgorithm == 1:  # Re-raycast
                        applyJitterWithReRaycast(intersected, self.uiValues, self.transform, self.targetList, self.worldUp)
                    # For simple jitter, we'll do it after object creation as before
                
                # create object
                intersected.createdObjectDAG(self.createObject(intersected))
                intersected.setInitialScale()
                self.strokeIntersectionList.addPoint(intersected)

                # simple jitter after object creation (if not re-raycast)
                if self.uiValues.jitter and self.uiValues.jitterAlgorithm != 1:
                    u = self.transform.getRandomJitter('uJitter')
                    v = self.transform.getRandomJitter('vJitter')
                    yOffset = math.fabs(self.worldUp.y - 1) * v
                    zOffset = math.fabs(self.worldUp.z - 1) * v
                    mc.move(u, yOffset, zOffset, intersected.generatedDAG, relative=True)

                # real-time rampFX
                if self.uiValues.realTimeRampFX:
                    self.rampFX(self.strokeIntersectionList)

        if sp3d_dbg:
            logDebugInfo('finished paintContext onDrag')
        forceRefresh()
        self.reentrance = 0

    def rampFX(self, objectList):
        '''
        operates the ramp FX on the passed intersectionList
        '''
        if self.uiValues.rampFX:
            nbObj = objectList.getLength()
            currentObj = 0.0
            scaleX, scaleY, scaleZ = self.transform.scale
            rotateX, rotateY, rotateZ = self.transform.rotate

            scaleAmplitudeX = scaleX[1] - scaleX[0]
            scaleAmplitudeY = scaleY[1] - scaleY[0]
            scaleAmplitudeZ = scaleZ[1] - scaleZ[0]

            rotateAmplitudeX = rotateX[1] - rotateX[0]
            rotateAmplitudeY = rotateY[1] - rotateY[0]
            rotateAmplitudeZ = rotateZ[1] - rotateZ[0]

            for obj in objectList.intersectionList:
                currentObj += 1.0  # ensure float division

                if self.uiValues.rampFX != 1:
                    currentObjScaleX = scaleX[0] + scaleAmplitudeX * (currentObj / nbObj)
                    currentObjScaleY = currentObjScaleZ = currentObjScaleX
                    if not self.uiValues.transformScaleUniform:
                        currentObjScaleY = scaleY[0] + scaleAmplitudeY * (currentObj / nbObj)
                        currentObjScaleZ = scaleZ[0] + scaleAmplitudeZ * (currentObj / nbObj)
                    mc.scale(
                        currentObjScaleX * obj.initialScale[0],
                        currentObjScaleY * obj.initialScale[1],
                        currentObjScaleZ * obj.initialScale[2],
                        obj.generatedDAG,
                        relative=False
                    )
                    if sp3d_ramp:
                        print("rampFX (Scale) obj# %i / %i (percent: %f) %s -> X %f Y %f Z %f" % (
                            currentObj, nbObj, (currentObj / nbObj), obj.generatedDAG,
                            currentObjScaleX, currentObjScaleY, currentObjScaleZ))

                if self.uiValues.rampFX != 2:
                    currentObjRotateX = rotateX[0] + rotateAmplitudeX * (currentObj / nbObj)
                    currentObjRotateY = rotateY[0] + rotateAmplitudeY * (currentObj / nbObj)
                    currentObjRotateZ = rotateZ[0] + rotateAmplitudeZ * (currentObj / nbObj)
                    # Use object-space rotation to preserve surface alignment
                    mc.rotate(currentObjRotateX, currentObjRotateY, currentObjRotateZ, obj.generatedDAG, os=True, r=True, rotateXYZ=True)

    def onRelease(self):
        '''
        on mouse release event: CLEANUP & rampFX if needed
        '''
        if not self.uiValues.realTimeRampFX:
            self.rampFX(self.strokeIntersectionList)

        if self.uiValues.hierarchy:
            # grouping objects
            g = int(self.uiValues.group)
            if g == 0:
                groupName = self.uiValues.getGroupID()
                for obj in self.strokeIntersectionList.intersectionList:
                    if not mc.objExists(groupName):
                        groupName = mc.group(empty=True, name=groupName)
                    # Always use long names for parenting
                    child = mc.ls(obj.generatedDAG, long=True)[0]
                    parent = mc.ls(groupName, long=True)[0]
                    # Only parent if not already parented
                    parents = mc.listRelatives(child, parent=True, fullPath=True) or []
                    if not parents or parents[0] != parent:
                        mc.parent(child, parent, relative=True)

            elif g == 1:
                groupName = mc.group(empty=True, name='spPaint3dStrokeOutput')
                parent = mc.ls(groupName, long=True)[0]
                for obj in self.strokeIntersectionList.intersectionList:
                    child = mc.ls(obj.generatedDAG, long=True)[0]
                    parents = mc.listRelatives(child, parent=True, fullPath=True) or []
                    if not parents or parents[0] != parent:
                        mc.parent(child, parent, relative=True)

            elif g == 2:
                for obj in self.strokeIntersectionList.intersectionList:
                    shapeParent = mc.listRelatives(obj.dagMeshSourceObject, parent=True, fullPath=True)
                    groupName = 'spPaint3dOutput_' + (shapeParent[0] if shapeParent else obj.dagMeshSourceObject)
                    if not mc.objExists(groupName):
                        groupName = mc.group(name=groupName, empty=True)
                    child = mc.ls(obj.generatedDAG, long=True)[0]
                    parent = mc.ls(groupName, long=True)[0]
                    parents = mc.listRelatives(child, parent=True, fullPath=True) or []
                    if not parents or parents[0] != parent:
                        mc.parent(child, parent, relative=True)

        # last cleanup, removing the temp group if it exists and is empty
        if getattr(self, "tempgroup", None) and mc.objExists(self.tempgroup):
            if sp3d_log:
                print("tempGroup exists, attempting to remove if empty")
            if not mc.listRelatives(self.tempgroup, children=True):
                if sp3d_log:
                    print("tempGroup (%s) is empty, removing." % self.tempgroup)
                mc.delete(self.tempgroup)

    def createObject(self, intersection):
        '''
        will create the object at the intersection object gathered data, pending all ui and transform options
        will update the stored data to store the created object DAG path and return the newly created object DAG Path back
        '''
        # Determine the source object to duplicate/instance
        sourceDAG = intersection.dagMeshSourceObject
        
        # Check if sourceDAG is already a transform or if we need to get its parent
        if mc.nodeType(sourceDAG) == 'transform':
            # Already a transform (could be a group or object transform)
            targetToClone = sourceDAG
        else:
            # It's a shape, get its parent transform
            tempDAG = mc.listRelatives(sourceDAG, parent=True)
            if not tempDAG:
                print("Error: No parent transform found for shape: %s" % sourceDAG)
                return None
            targetToClone = tempDAG[0]
        
        # instance or duplicate
        if self.uiValues.instance:
            if sp3d_dbg:
                logDebugInfo('creating instance')
            newObjectDAG = mc.instance(targetToClone)
        else:
            if sp3d_dbg:
                logDebugInfo('duplicating object')
            newObjectDAG = mc.duplicate(targetToClone, ic=self.uiValues.preserveConn)

        if sp3d_dbg:
            logDebugInfo('DONE creating instance / duplicating object')

        # Always convert to long names (namespace-safe)
        newObjectDAG = [mc.ls(obj, long=True)[0] for obj in newObjectDAG]

        # When duplicating groups, Maya returns [group, child1, child2, ...] 
        # We only need the top-level group/object
        if len(newObjectDAG) > 1:
            if mc.nodeType(newObjectDAG[0]) == 'transform':
                newObjectDAG = [newObjectDAG[0]]
            else:
                topLevelNodes = []
                fullPaths = [mc.ls(dag, long=True)[0] for dag in newObjectDAG]
                for i, dag in enumerate(fullPaths):
                    parents = mc.listRelatives(dag, parent=True, fullPath=True) or []
                    isTopLevel = True
                    for parent in parents:
                        if parent in fullPaths:
                            isTopLevel = False
                            break
                    if isTopLevel:
                        topLevelNodes.append(newObjectDAG[i])
                if len(topLevelNodes) == 1:
                    newObjectDAG = topLevelNodes
                elif len(topLevelNodes) > 1:
                    print("Warning: Multiple top-level objects created, using first: %s" % topLevelNodes[0])
                    newObjectDAG = [topLevelNodes[0]]
                else:
                    print("Warning: No top-level objects found, using original first: %s" % newObjectDAG[0])
                    newObjectDAG = [newObjectDAG[0]]

        # move to hit point
        moveTo(newObjectDAG[0], intersection.hitPoint)

        # align to surface normal
        if self.uiValues.align:
            if sp3d_dbg:
                logDebugInfo('aligning object with surface normal')
            rx, ry, rz = getEulerRotationQuaternion(self.worldUp, intersection.getHitNormal(self.uiValues.smoothNormal))
            mc.xform(newObjectDAG[0], ro=(rx, ry, rz))
            if sp3d_dbg:
                logDebugInfo('DONE aligning object with surface normal')

        # random rotate / scale (skipped if rampFX drives them)
        if self.uiValues.transformRotate and not self.uiValues.rampFX:
            randrotate = self.transform.getRandomRotate(self.uiValues)
            mc.rotate(randrotate[0], randrotate[1], randrotate[2], newObjectDAG[0], os=True, r=True, rotateXYZ=True)

        if self.uiValues.transformScale and not self.uiValues.rampFX:
            randscale = self.transform.getRandomScale(self.uiValues.transformScaleUniform)
            mc.scale(randscale[0], randscale[1], randscale[2], newObjectDAG[0], relative=True)

        # up offset
        if self.uiValues.upOffset != 0:
            offsetArray = [
                self.uiValues.upOffset * self.worldUp.x,
                self.uiValues.upOffset * self.worldUp.y,
                self.uiValues.upOffset * self.worldUp.z
            ]
            mc.move(offsetArray[0], offsetArray[1], offsetArray[2], newObjectDAG[0], relative=True)

        # ensure created object is visible if forceVisibility option is enabled
        if self.uiValues.forceVisibility:
            mc.setAttr(newObjectDAG[0] + '.visibility', 1)

        # tempgroup parenting only when hierarchy is enabled
        if self.uiValues.hierarchy:
            # Create tempgroup if it doesn't exist
            if not getattr(self, 'tempgroup', None) or not mc.objExists(self.tempgroup):
                self.tempgroup = mc.group(empty=True, name=spPaint3dTempGroupID)
                if sp3d_log:
                    print("Created tempgroup: %s" % self.tempgroup)
            
            # Parent to tempgroup
            grouped = mc.parent(newObjectDAG[0], self.tempgroup, relative=True)
            return grouped[0]

        # fallback: return original transform (no hierarchy grouping)
        return newObjectDAG[0]

    def runtimeUpdate(self, uioptions, transformoptions, sourcelist, targetlist):
        '''
        entry method used from GUI to pass changes in the UI options through self.ctx.runtimeUpdate(...)
        '''
        self.uiValues = uioptions
        self.transform = transformoptions
        self.sourceList = sourcelist
        self.targetList = targetlist




#-------------------------------
# Misc Utils
#-------------------------------

def forceRefresh():
    '''
    force a current viewport refresh
    '''
    mc.refresh(cv=True)


def moveTo(dag, pos, rot=None):
    '''
    move the dag object to pos position
    attemps to compensate for unfrozen transform by reading the scalepivot of the object
    '''
    scalePivot = mc.xform(dag, query=True, ws=True, sp=True)
    transform = mc.xform(dag, query=True, ws=True, t=True)

    mc.xform(dag, t=( (transform[0]-scalePivot[0])+pos.x, (transform[1]-scalePivot[1])+pos.y, (transform[2]-scalePivot[2])+pos.z ))
    if (rot):
        if sp3d_log: print (rot)
        mc.rotate(rot[0], rot[1], rot[2], dag, os=True, r=True, rotateXYZ=True)


def getPosition(dag):
    '''
    retrieve the world position of the dag parameter object and return a point object containing the position
    '''
    tempdag = dag
    if (mc.nodeType(tempdag)!='transform'):
        #get the transform to that shape
        temprelatives = mc.listRelatives(tempdag, parent=True)
        tempdag=temprelatives[0]

    scalePivot = mc.xform(tempdag, query=True, ws=True, sp=True)
    transform = mc.xform(tempdag, query=True, ws=True, t=True)

    return point( (transform[0]-scalePivot[0]), (transform[1]-scalePivot[1]), (transform[2]-scalePivot[2]) )


def getEulerRotationQuaternion(upvector, directionvector):
    '''
    returns the x,y,z degree angle rotation corresponding to a direction vector
    input: upvector (MVector) & directionvector (MVector)
    '''
    quat = om.MQuaternion(upvector, directionvector)
    quatAsEuler = om.MEulerRotation()
    quatAsEuler = quat.asEulerRotation()

    return math.degrees(quatAsEuler.x), math.degrees(quatAsEuler.y), math.degrees(quatAsEuler.z)


def getViewportClick(screenX, screenY):
    '''
    return world position and direction of the viewport clicked point (returns point objects)
    '''
    maya3DViewHandle = omui.M3dView()
    activeView = maya3DViewHandle.active3dView()

    clickPos = om.MPoint()
    clickDir = om.MVector()

    activeView.viewToWorld(int(screenX), int(screenY), clickPos, clickDir)

    worldPos = point(clickPos.x, clickPos.y, clickPos.z)
    worldDir = point(clickDir.x, clickDir.y, clickDir.z)

    return worldPos,worldDir



def getCameraFarClip():
    '''
    Return current camera far clip
    '''
    maya3DViewHandle = omui.M3dView()
    activeView = maya3DViewHandle.active3dView()

    cameraDP = om.MDagPath()
    maya3DViewHandle.active3dView().getCamera(cameraDP)

    camFn = om.MFnCamera(cameraDP)
    return camFn.farClippingPlane()


def applyJitterWithReRaycast(intersected, uiValues, transform, targetList, worldUp):
    '''
    Apply jitter using re-raycast algorithm - each jittered position gets a new raycast to find the actual surface
    '''
    if not uiValues.jitter:
        return
    
    u = transform.getRandomJitter('uJitter')
    v = transform.getRandomJitter('vJitter')
    
    # Get original intersection point
    originalPos = intersected.hitPoint
    
    # Calculate jittered position - simple XZ plane jitter
    jitteredX = originalPos.x + u
    jitteredZ = originalPos.z + v  # Use v for Z-axis jitter
    
    # Perform raycast from well above the jittered XZ position, straight down
    raycastHeight = 2000  # Start much higher to ensure we're above any geometry
    raycastStart = point(jitteredX, originalPos.y + raycastHeight, jitteredZ)
    raycastDir = point(0, -1, 0)  # Straight down direction
    
    # Try to find intersection at jittered position
    newIntersection = targetSurfaceLoopIntersect(targetList, raycastStart, raycastDir)
    
    if newIntersection:
        # Use the new intersection point and all available attributes
        intersected.hitPoint = newIntersection.hitPoint
        intersected.hitFace = newIntersection.hitFace
        intersected.hitTriangle = newIntersection.hitTriangle  # Correct attribute name
        intersected.dagMeshTargetSurface = newIntersection.dagMeshTargetSurface

def targetSurfaceLoopIntersect(targetList, clickPos, clickDir):
    '''
    loop through all the object in targetList and intersect them with click (world pos, direction). creates an intersectionPoint object for each intersection
    sort the list of intersection and return the closest intersectionPoint object from the click world position, return None if no intersection found
    '''
    ilist = intersectionList()
    farclip = getCameraFarClip()
    for obj,data in targetList.obj.items():
        #loop through each object in the targetList
        intersected = intersectTargetSurface(data[0], clickPos, clickDir, farclip)
        if (intersected):
            #got meh an intersected
            ilist.addPoint(intersected)

    return ilist.getClosest(clickPos)


def intersectTargetSurface(targetdag, clickPos, clickDir, farclip=1.0):
    '''
    intersect a single object from the click world pos and direction. optional farclip distance
    return an intersectionPoint object if there was any intersection
    return None otherwise
    '''
    currentHitFP = om.MFloatPoint() #current intersection
    hitFace = om.MScriptUtil()
    hitTri = om.MScriptUtil()

    hitFace.createFromInt(0)
    hitTri.createFromInt(0)

    hitFaceptr = hitFace.asIntPtr()
    hitTriptr = hitTri.asIntPtr()

    targetDAGPath = getDAGObject(targetdag)

    if (targetDAGPath):
        #returned targetDAGPath is sort of valid
        fnMesh = om.MFnMesh( targetDAGPath )
        hit = fnMesh.closestIntersection( clickPos.asMFPoint(),
                                clickDir.asMFVector(),
                                None,
                                None,
                                True,
                                om.MSpace.kWorld,
                                farclip,
                                True,
                                None,
                                currentHitFP,
                                None,
                                hitFaceptr,
                                hitTriptr,
                                None,
                                None)
        if (hit):
            #there was a positive intersection
            if (sp3d_MFn): print ("Face Hit: %i || Tri Hit: %i" % (hitFace.getInt(hitFaceptr),hitTri.getInt(hitTriptr)))
            return intersectionPoint(point(currentHitFP.x, currentHitFP.y, currentHitFP.z), hitFace.getInt(hitFaceptr), hitTri.getInt(hitTriptr), targetDAGPath)

    #reaches here only if no intersection or not a valid targetDAGPath
    return None




def getDAGObject(dagstring):
    '''
    return the DAG Api object from the dagstring argument
    return None if the minimum checks on dagstring don't checkout
    '''
    sList = om.MSelectionList()
    meshDP = om.MDagPath()
    #sList.clear() #making sure to clear the content of the MSelectionList in case we are looping through multiple objects
    om.MGlobal.getSelectionListByName(dagstring, sList)
    sList.getDagPath(0,meshDP)

    return meshDP

def getDistanceBetween(source,target):
    '''
    return the distance between source and target
    '''
    distance = math.sqrt(    math.pow((source.x - target.x), 2) +
                                math.pow((source.y - target.y), 2) +
                                math.pow((source.z - target.z), 2) )
    return distance

def getCorrectedDistance(distance, unit):
    '''
    return the corrected distance using proper unit to convert back to centimeters
    '''
    if(unit=='cm'): return distance
    else: return (distance/(sp3dUnit[unit]))

def logDebugInfo(info):
    '''
    overwrite the default debug file content with <info>
    '''
    with open(sp3d_dbgfile,'w') as f:
        f.write(info)
