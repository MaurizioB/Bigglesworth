from copy import deepcopy
import numpy as np
from uuid import UUID

from Qt import QtCore

from bigglesworth.utils import sanitize
from bigglesworth.wavetables.utils import baseSineValues, pow20, pow22, noteFrequency


class KeyFrames(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, container):
        QtCore.QObject.__init__(self)
        self.container = container
        self.layout = container.layout()
        self.fullValues = [baseSineValues[:] for _ in range(64)]
        firstItem = SampleItem(self)
        firstItem.setFirst(True)
        firstTransform = WaveTransformItem(self, 0, firstItem)
        firstTransform.prevWaveIndex = 0
        self.keyFrames = [firstItem]
        self.fullList = self.keyFrames + [None for _ in range(63)]
        self.allItems = [firstItem, firstTransform]

        for item in self.allItems:
            self.layout.addItem(item)

        self.clean = False
        self.fullAudioValues = None
        self.currentNote = None
        self.multiplier = None

    @property
    def scene(self):
        try:
            return self._scene
        except:
            scene = self.container.scene()
            if scene is not None:
                self._scene = scene
            return scene

    def setValuesDirty(self):
        self.clean = False

    def sanitize(self, value):
        return sanitize(-pow20, value, pow20)

#    def rebuild(self):
#        self.fullList = [None for _ in range(64)]
#        for keyFrame in self.keyFrames:
#            self.fullList[keyFrame.index] = keyFrame
#        self.clean = True

    def get(self, index):
        try:
            return self.fullList[index]
        except:
            print('invalid index {}!!!'.format(index))
            return None

    def getClosestValidIndex(self, index, direction=0):
        delta = 1
        while True:
            if direction <= 0:
                newIndex = index - delta
                if newIndex >= 0 and self.fullList[newIndex]:
                    return newIndex
                if direction < 0 and newIndex < 0:
                    return None
            if direction >= 0:
                newIndex = index + delta
                if newIndex <= 63 and self.fullList[newIndex]:
                    return newIndex
                if direction > 0 and newIndex > 63:
                    return None
            delta += 1
            if delta > 63:
                return None

    def getClosestValidKeyFrame(self, index, direction=0):
        return self.get(self.getClosestValidIndex(index, direction))

    def setValue(self, index, sample, value):
        value = self.sanitize(value)
        self.fullValues[index][sample] = value
        self.get(index).setWaveValue(sample, value)

    def setValues(self, index, data):
        if len(data) == 1:
            self.setValue(index, data.keys()[0], data.values()[0])
#            self.get(index).setValue(values.keys()[0], values.values()[0])
        else:
            if isinstance(data, dict):
                samples = data.keys()
                values = data.values()
            elif isinstance(data[0], (float, int, np.floating)):
                samples = range(128)
                values = data
            else:
                samples, values = zip(*data)
            values = map(self.sanitize, values)
            valueList = self.fullValues[index]
            data = zip(samples, values)
            for sample, value in data:
                valueList[sample] = value
            self.get(index).setWaveValues(data)

    def setValuesMulti(self, start, sourceData, fromFile=False):
        count = len(sourceData)
        data = {}
        allItems = []
        keyFrames = []
        if count != 64:
            invalidTransforms = {}
            for item in self.allItems:
                if isinstance(item, WaveTransformItem) and not item.isValid() and \
                    not isinstance(item.nextItem, SampleItem) and item.prevWaveIndex is not None:
                        invalidTransforms[item.prevWaveIndex] = item
            prevTransform = None
            sourceData = iter(sourceData)
            indexRange = range(start, start + count)
            for w in range(64):
                keyFrame = self.fullList[w]
                if keyFrame:
                    keyFrames.append(keyFrame)
                    allItems.append(keyFrame)
                    if w in indexRange:
                        data[w] = sourceData.next()
                        if prevTransform and prevTransform.nextItem != keyFrame:
                            prevTransform.setNextItem(keyFrame)
                    prevTransform = keyFrame.nextTransform
                    if prevTransform:
                        allItems.append(prevTransform)
                elif w in indexRange:
                    data[w] = sourceData.next()
                    keyFrame = SampleItem(self)
                    allItems.append(keyFrame)
                    self.fullList[w] = keyFrame
                    keyFrames.append(keyFrame)
                    if prevTransform:
                        prevTransform.setNextItem(keyFrame)
                    if w in invalidTransforms:
                        prevTransform = invalidTransforms[w]
                        prevTransform.setPrevItem(keyFrame)
                    else:
                        prevTransform = WaveTransformItem(self, 0, keyFrame)
                    allItems.append(prevTransform)
        else:
            prevTransform = None
            sourceData = iter(sourceData)
            for w in range(64):
                data[w] = sourceData.next()
                keyFrame = SampleItem(self)
                allItems.append(keyFrame)
                self.fullList[w] = keyFrame
                keyFrames.append(keyFrame)
                if prevTransform:
                    prevTransform.setNextItem(keyFrame)
                if w < 63:
                    prevTransform = WaveTransformItem(self, 0, keyFrame)
                    allItems.append(prevTransform)
        for item in self.allItems:
#            if isinstance(item, WaveTransformItem):
#                item.setTargets(None, None)
            self.layout.removeItem(item)
        self.allItems[:] = allItems
        self.keyFrames[:] = keyFrames
        for item in self.allItems:
            self.layout.addItem(item)
        if fromFile:
            for index, data in data.items():
                self.setValues(index, list(data * pow20))
        else:
            for index, data in data.items():
                self.setValues(index, list(data))

        for item in self.allItems:
            if isinstance(item, WaveTransformItem):
#                if not item.isValid():
#                    print(type(item.prevItem), type(item.nextItem))
                item.updateGeometry()
        if isinstance(self.allItems[-1], WaveTransformItem) and self.allItems[-1].nextItem != self.keyFrames[0]:
            self.allItems[-1].setNextItem(self.keyFrames[0])
        self.scene.changed.emit()
        if not self.scene.maximized:
            self.allItems[1].minimize()
        self.layout.invalidate()
        self.clean = False
        self.changed.emit()

    def getLayoutIndex(self, item):
        for index in range(self.layout.count()):
            _item = self.layout.itemAt(index)
            if _item == item:
                return index
        return None

    def setDataFromDropSelection(self, data, dropData):
        targets, overwrite, movedBefore, movedAfter = dropData
#        changed = []
        targetRange = range(min(targets), max(targets) + 1)
        invalidTransforms = {}
        for item in self.allItems:
            if isinstance(item, WaveTransformItem) and not item.isValid() and \
                not isinstance(item.prevItem, SampleItem) and item.prevWaveIndex is not None and item.prevWaveIndex in targetRange:
                    invalidTransforms[item.prevWaveIndex] = item
        print(movedBefore, movedAfter)
        print('procedo')
        if not (movedBefore or movedAfter):
            if not overwrite or overwrite == targets:
                dropValues = [d[1] for d in data if d[0] == SampleItem]
                self.setValuesMulti(targets[0], dropValues)
                return

    def setValuesFromDrop(self, dropValues, dropData, fromFile=False):
        targets, overwrite, movedBefore, movedAfter = dropData
        changed = []
        targetRange = range(min(targets), max(targets) + 1)
        invalidTransforms = {}
        for item in self.allItems:
            if isinstance(item, WaveTransformItem) and not item.isValid() and \
                not isinstance(item.prevItem, SampleItem) and item.prevWaveIndex is not None and item.prevWaveIndex in targetRange:
                    invalidTransforms[item.prevWaveIndex] = item
        print(movedBefore, movedAfter)
        if not (movedBefore or movedAfter):
            if not overwrite or overwrite == targets:
                print(dropValues[0])
                self.setValuesMulti(targets[0], dropValues, fromFile)
                return
#                beforeItem = self.getClosestValidKeyFrame(min(targets), -1)
#                if beforeItem is None:
#                    beforeItem = self.keyFrames[0]
#                afterItem = self.getClosestValidKeyFrame(max(targets), 1)
#                if afterItem is None:
#                    afterItem = self.keyFrames[0]
#                beforeTransform = prevTransform = beforeItem.nextTransform
#                layoutTarget = self.getLayoutIndex(beforeTransform)
#                newItems = []
#                for index, values in zip(targets, dropValues):
#                    waveItem = SampleItem(self)
#                    if afterItem == self.keyFrames[0]:
#                        self.keyFrames.append(waveItem)
#                    else:
#                        self.keyFrames.insert(self.keyFrames.index(afterItem), waveItem)
#                    self.fullValues[index] = values
#                    self.fullList[index] = waveItem
#                    prevTransform.setNextItem(waveItem)
#                    newItems.append(waveItem)
#                    if index in invalidTransforms:
#                        prevTransform = invalidTransforms[index]
#                        prevTransform.setPrevItem(waveItem)
#                        self.allItems.remove(prevTransform)
#                    else:
#                        if index == targets[-1]:
#                            prevTransform = beforeTransform.clone(waveItem, afterItem)
#                        else:
#                            prevTransform = WaveTransformItem(self, 0, waveItem)
#                    newItems.append(prevTransform)
#                self.allItems[layoutTarget:layoutTarget] = newItems
#                existing = self.scene.items()
#                for index, item in enumerate(self.allItems):
#                    if item not in existing:
#                        self.layout.insertItem(index, item)
#            elif targets == overwrite:
#                for index, values in zip(targets, dropValues):
#                    self.fullValues[index] = values
#                    changed.append(self.fullList[index])

        self.scene.changed.emit()
        if not self.scene.maximized:
            self.allItems[1].minimize()
        [k.changed.emit() for k in changed]
        self.layout.invalidate()
        self.clean = False

    def merge(self, start, end):
        items = []
        for i in range(start + 1, end):
            item = self.fullList[i]
            if item:
                items.append(item)
#        lastTransform = item.nextTransform
        if len(items) <= 2:
            return
        self.deleteKeyFrames(items)
#        self.deleteTransform(lastTransform)
        firstTransform = self.fullList[start].nextTransform
        firstTransform.setNextItem(self.fullList[end])
        firstTransform.setMode(1)
        self.changed.emit()

    def bounce(self, firstIndex, lastIndex):
        firstItem = self.fullList[firstIndex]
        transform = firstItem.nextTransform
        firstValues = self.fullValues[firstIndex][:]
        data = []
        if not transform.mode:
            for i in range(lastIndex - firstIndex):
                data.append(firstValues)
        elif transform.isLinear():
            firstValues = np.array(firstValues)
            lastValues = np.array(self.fullValues[lastIndex])
            diff = lastIndex - firstIndex
            ratio = 1. / diff
            for index in range(lastIndex - firstIndex + 1):
                percent = index * ratio
                deltaArray = (1 - percent) * firstValues + percent * lastValues
                data.append(deltaArray.tolist())
        elif transform.mode == transform.CurveMorph:
            firstValues = np.array(firstValues)
            lastValues = np.array(self.fullValues[lastIndex])
            diff = lastIndex - firstIndex
            ratio = 1. / diff
            curveFunc = transform.curveFunction
            for index in range(diff):
                percent = curveFunc(index * ratio)
                deltaArray = (1 - percent) * firstValues + percent * lastValues
                data.append(deltaArray.tolist())
        elif transform.mode == transform.TransMorph:
            firstValues = np.array(firstValues)
            lastValues = np.roll(np.array(self.fullValues[lastIndex]), -transform.translate)
            diff = lastIndex - firstIndex
            ratio = 1. / diff
            for index in range(lastIndex - firstIndex + 1):
                percent = index * ratio
                deltaArray = np.roll((1 - percent) * firstValues + percent * lastValues, int(transform.translate * percent))
                data.append(deltaArray.tolist())
        elif transform.mode == transform.SpecMorph:
            firstValues = np.array(firstValues)
            lastValues = np.array(self.fullValues[lastIndex])
            diff = lastIndex - firstIndex
            ratio = 1. / diff
            harmonicsArrays = transform.getHarmonicsArray()
            for index in range(diff):
                percent = index * ratio
                deltaArray = (1 - percent) * firstValues + percent * lastValues
                np.clip(np.add(deltaArray, harmonicsArrays[index]), -pow20, pow20, out=deltaArray)
                data.append(deltaArray.tolist())
        self.setValuesMulti(firstIndex, data)

    def reverse(self, start, end):
        if (start, end) == (0, 64):
            lastWave = self.fullList[63]
            if not lastWave:
                self.fullValues[63] = self.fullValues[0][:]
                lastWave = SampleItem(self)
                self.fullList[63] = lastWave
                self.allItems.append(lastWave)
                self.keyFrames.append(lastWave)
                try:
                    self.allItems[-2].setNextItem(lastWave)
                except:
                    raise('Last item was not a transform?')
        affected = [i for i in self.fullList[start:end] if isinstance(i, SampleItem)]
        self.fullValues[start:end] = reversed(self.fullValues[start:end])
        self.fullList[start:end] = reversed(self.fullList[start:end])
        self.keyFrames[:] = [i for i in self.fullList if isinstance(i, SampleItem)]
        layoutStart = self.getLayoutIndex(affected[0])
        try:
            layoutEnd = self.getLayoutIndex(affected[-1]) + 1
        except:
            layoutEnd = len(self.allItems)
        reversedItems = list(reversed(self.allItems[layoutStart:layoutEnd]))
        self.allItems[layoutStart:layoutEnd] = reversedItems
        for item in reversed(reversedItems):
            try:
                self.layout.removeItem(item)
            except:
                pass
            self.layout.insertItem(layoutStart, item)

        transforms = []
        for layoutIndex, item in enumerate(self.allItems):
            if isinstance(item, WaveTransformItem):
                transforms.append(item)
                try:
                    item.setTargets(self.allItems[layoutIndex - 1], self.allItems[layoutIndex + 1])
                except:
                    item.setTargets(self.allItems[layoutIndex - 1], self.keyFrames[0])
        self.clean = False
        [k.changed.emit() for k in self.keyFrames]
        self.scene.changed.emit()
        self.layout.invalidate()
        self.changed.emit()

    def distribute(self, start, end):
        count = end - start
        items = [i for i in self.fullList[start:end] if i]
        ratio = float(count) / len(items)
        data = {}
        oldIndexes = []
        for i, keyFrame in enumerate(items):
            index = start + int(i * ratio)
            data[index] = keyFrame, keyFrame.values[:]
            oldIndexes.append(keyFrame.index)
        for index in sorted(data.keys()):
            keyFrame, values = data[index]
            self.fullList[index] = keyFrame
            self.fullValues[index] = values
        for oldIndex in oldIndexes:
            if oldIndex not in data:
                self.fullList[oldIndex] = None
        self.clean = False
        [k.changed.emit() for k in items]
        self.invalidateTransforms()
        self.scene.changed.emit()
        self.layout.invalidate()
        self.changed.emit()

    def isValid(self):
        items = iter(self.allItems)
        while True:
            try:
                assert isinstance(items.next(), SampleItem)
                assert isinstance(items.next(), WaveTransformItem)
            except StopIteration:
                return True
            except AssertionError:
                return False

    def isExternal(self, item):
        return item in (self.fullList[0], self.fullList[-1])

    def index(self, item):
        try:
            return self.fullList.index(item)
        except:
#            print('index requested, but not found', item, self.sender())
            return None

    def values(self, item):
        return self.fullValues[self.fullList.index(item)]

    def previous(self, index):
        if isinstance(index, SampleItem):
            index = self.fullList.index(index)
            if index is None:
                return None
        for item in reversed(self.fullList[:index]):
            if isinstance(item, SampleItem):
                return item

    def previousIndex(self, index):
        return self.index(self.previous(index))

    def next(self, index):
        if isinstance(index, SampleItem):
            index = self.fullList.index(index)
            if index is None:
                return None
        for item in self.fullList[index + 1:]:
            if isinstance(item, SampleItem):
                return item

    def nextIndex(self, index):
        nextItem = self.next(index)
        if nextItem is None:
            return -1
        return self.index(nextItem)

    def prevTransform(self, item):
        itemIndex = self.allItems.index(item)
        if itemIndex:
            return self.allItems[itemIndex - 1]
        return self.allItems[-1]

    def nextTransform(self, item):
        try:
            return self.allItems[self.allItems.index(item) + 1]
        except:
            return None

    def createAt(self, index, values=None, after=False):
        keyFrame = SampleItem(self)
        keyFrame.changed.connect(self.setValuesDirty)
        transforms = set()
        if index < 0:
            shifted = []
            for item in self.fullList:
                if item is None:
                    break
                else:
                    shifted.append(item)
            self.fullList[1:len(shifted) + 1] = shifted
            self.fullList[0] = keyFrame
            self.keyFrames.insert(0, keyFrame)
            self.allItems.insert(0, keyFrame)
            oldFirst = self.keyFrames[0]
            transform = WaveTransformItem(self, 0, keyFrame, oldFirst)
            transforms.add(transform)
            self.allItems.insert(1, transform)
            self.layout.insertItem(0, keyFrame)
            self.layout.insertItem(1, transform)
            oldFirst.setFirst(False)
            keyFrame.setFirst(True)
        else:
            if self.fullList[index] is not None:
#                print(self.fullList)
                #checking if there is actually room for the requested action
                if after:
                    for item in self.fullList[index:]:
                        if item is None:
                            break
                    else:
                        after = False
                else:
                    for item in reversed(self.fullList[:index + 1]):
                        if item is None:
                            break
                    else:
                        index += 1
                        after = True
                shifted = []
                if after:
                    for item in self.fullList[index:]:
                        if item is None:
                            break
                        else:
                            shifted.append(item)
                    self.fullList[index + 1:len(shifted) + 1] = shifted
                else:
                    for delta, item in enumerate(reversed(self.fullList[:index + 1]), 1):
                        if item is None:
                            break
                        else:
                            shifted.append(item)
                    self.fullList[index - delta:len(shifted) + 1] = reversed(shifted)
            self.fullList[index] = keyFrame
#            print(keyFrame, self.fullList)
            prevItem = self.previous(keyFrame)
            prevTransformIndex = self.allItems.index(prevItem) + 1
            prevTransform = self.allItems[prevTransformIndex]
            transforms.add(prevTransform)
#            prevTransform.setNextItem(keyFrame)
            if index == 63:
                self.keyFrames[-1].setFinal(False)
                self.keyFrames.append(keyFrame)
                self.allItems.append(keyFrame)
                self.layout.addItem(keyFrame)
                keyFrame.setFinal(True)
            else:
                self.keyFrames.insert(self.keyFrames.index(prevItem) + 1, keyFrame)
                if prevTransformIndex == self.allItems[-1]:
                    transform = prevTransform.clone(keyFrame, prevItem)
                    transforms.add(transform)
                    self.allItems.append(keyFrame)
                    self.allItems.append(transform)
                    self.layout.addItem(transform)
                else:
                    self.allItems.insert(prevTransformIndex + 1, keyFrame)
                    self.layout.insertItem(prevTransformIndex + 1, keyFrame)
                    if prevTransformIndex + 2 == len(self.allItems):
                        nextItem = None
                    else:
                        nextItem = self.allItems[prevTransformIndex + 2]
                    if not isinstance(nextItem, WaveTransformItem):
                        transform = prevTransform.clone(keyFrame, nextItem)
                        transforms.add(transform)
                        self.allItems.insert(prevTransformIndex + 2, transform)
                        if nextItem is None:
#                            transform.nextItem = self.keyFrames[0]
                            transform.setNextItem(self.keyFrames[0])
                        self.layout.insertItem(prevTransformIndex + 2, transform)
        if values is not None:
            self.setValues(keyFrame.index, values[:])
        for transform in transforms | self.invalidateTransforms():
            transform.updateGeometry()
        self.scene.changed.emit()
        if not self.scene.maximized:
            self.allItems[1].minimize()
        self.layout.invalidate()
        self.clean = False
        try:
            return keyFrame
        finally:
            self.changed.emit()

    def moveKeyFrames(self, keyFrames, newStartIndex):
        if len(keyFrames) == 1:
            self.moveKeyFrame(keyFrames[0], newStartIndex)
            return
        delta = newStartIndex - keyFrames[0].index
        values = {}
        prevIndexes = {}
        for keyFrame in keyFrames:
            index = keyFrame.index
            values[keyFrame] = self.fullValues[index][:]
            prevIndexes[keyFrame] = self.index(keyFrame)
        newIndexes = {}
        for keyFrame in keyFrames:
            prevIndex = prevIndexes[keyFrame]
            newIndex = prevIndex + delta
            newIndexes[keyFrame] = newIndex
            self.fullList[newIndex] = keyFrame
            self.fullValues[newIndex] = values[keyFrame]
        for keyFrame, index in prevIndexes.items():
            if index not in newIndexes.values():
                self.fullList[index] = None
                self.fullValues[index] = baseSineValues[:]
        if newIndex < 63 and self.keyFrames[-1] == keyFrame and not isinstance(self.allItems[-1], WaveTransformItem):
            transform = keyFrame.prevTransform.clone(keyFrame, self.keyFrames[0])
            self.allItems.append(transform)
            self.layout.addItem(transform)
        print(self.keyFrames, self.fullList)
        self.scene.changed.emit()
        [k.indexChanged.emit(i) for k, i in newIndexes.items()]
        self.clean = False
        self.changed.emit()

    def moveKeyFrame(self, keyFrame, newIndex):
        prevValidIndex = self.previousIndex(keyFrame)
        nextValidIndex = self.nextIndex(keyFrame)
        if nextValidIndex < 0:
            nextValidIndex = 64
        if not prevValidIndex < newIndex < nextValidIndex:
            print('wtf?!')
            raise BaseException('Invalid index range?')
            return
        prevIndex = self.index(keyFrame)
        self.fullList[newIndex] = keyFrame
        self.fullList[prevIndex] = None
#        print('keyFrame {} moved to {}: {}'.format(keyFrame, newIndex, self.fullList[newIndex]))
        self.fullValues[newIndex] = self.fullValues[prevIndex][:]
        self.fullValues[prevIndex] = baseSineValues[:]
        if newIndex < 63 and self.keyFrames[-1] == keyFrame and not isinstance(self.allItems[-1], WaveTransformItem):
            transform = keyFrame.prevTransform.clone(keyFrame, self.keyFrames[0])
            self.allItems.append(transform)
            self.layout.addItem(transform)
        self.scene.changed.emit()
        keyFrame.indexChanged.emit(newIndex)
        self.clean = False
        self.changed.emit()

    def deleteKeyFrame(self, keyFrame):
        prevTransform = keyFrame.prevTransform
        nextTransform = keyFrame.nextTransform
        if nextTransform and nextTransform.isContiguous():
            if nextTransform.nextItem:
                prevTransform.setNextItem(nextTransform.nextItem)
            self.allItems.remove(nextTransform)
            self.layout.removeItem(nextTransform)
            self.scene.removeItem(nextTransform)
        elif prevTransform.isContiguous():
            if prevTransform.prevItem and nextTransform:
                nextTransform.setPrevItem(prevTransform.prevItem)
            self.allItems.remove(prevTransform)
            self.layout.removeItem(prevTransform)
            self.scene.removeItem(prevTransform)
        else:            
            prevTransform.setNextItem(None)
            if nextTransform:
                nextTransform.setPrevItem(None)
        self.layout.removeItem(keyFrame)
        self.scene.removeItem(keyFrame)
        self.keyFrames.remove(keyFrame)
        self.fullList[self.fullList.index(keyFrame)] = None
        self.allItems.remove(keyFrame)
        if self.allItems[-1] == prevTransform:
            prevTransform.setNextItem(self.keyFrames[0])
        self.scene.changed.emit()
        self.clean = False
        self.changed.emit()

    def deleteKeyFrames(self, items):
        indexes = [self.fullList.index(item) for item in items]
        first = self.fullList[min(indexes)]
        last = self.fullList[max(indexes)]
        prevTransform = first.prevTransform
        nextTransform = last.nextTransform
        innerTransforms = []
        for i in range(self.allItems.index(first), self.allItems.index(last) + 1):
            item = self.allItems[i]
            if isinstance(self.allItems[i], WaveTransformItem):
                innerTransforms.append(item)
                self.layout.removeItem(item)
                self.scene.removeItem(item)
        [self.allItems.remove(item) for item in innerTransforms]
        if nextTransform.isContiguous():
            if nextTransform.nextItem:
                prevTransform.setNextItem(nextTransform.nextItem)
            self.allItems.remove(nextTransform)
            self.layout.removeItem(nextTransform)
            self.scene.removeItem(nextTransform)
        elif prevTransform.isContiguous():
            if prevTransform.prevItem:
                nextTransform.setPrevItem(prevTransform.prevItem)
            self.allItems.remove(prevTransform)
            self.layout.removeItem(prevTransform)
            self.scene.removeItem(prevTransform)
        else:            
            prevTransform.setNextItem(None)
            nextTransform.setPrevItem(None)
        for item in items:
            self.layout.removeItem(item)
            self.scene.removeItem(item)
            self.keyFrames.remove(item)
            self.fullList[self.fullList.index(item)] = None
            self.allItems.remove(item)
        if max(indexes) == 63 and isinstance(self.allItems[-1], WaveTransformItem):
            lastTransform = self.allItems[-1]
            self.allItems.remove(lastTransform)
            self.layout.removeItem(lastTransform)
            self.scene.removeItem(lastTransform)
        self.invalidateTransforms()
        self.scene.changed.emit()
        self.layout.invalidate()
        self.clean = False
        self.changed.emit()

    def deleteTransform(self, transform):
        if transform == self.allItems[-1] and isinstance(self.allItems[-2], WaveTransformItem):
            self.allItems[-2].setNextItem(self.keyFrames[0])
        elif transform == self.allItems[-2] and isinstance(self.allItems[-1],  WaveTransformItem):
            self.allItems[-1].setNextItem(self.keyFrames[0])
        else:
            index = self.allItems.index(transform)
            prevItem = self.allItems[index - 1]
            nextItem = self.allItems[index + 1]
            if isinstance(prevItem, SampleItem) and isinstance(nextItem, WaveTransformItem):
                nextItem.setPrevItem(prevItem)
            elif isinstance(prevItem, WaveTransformItem) and isinstance(nextItem, SampleItem):
                prevItem.setNextItem(nextItem)
        self.layout.removeItem(transform)
        self.scene.removeItem(transform)
        self.allItems.remove(transform)
        self.scene.changed.emit()
        self.layout.invalidate()
        self.clean = False
        self.changed.emit()

    def invalidateTransforms(self):
        changed = set()
        for i, item in enumerate(self.allItems):
            if isinstance(item, WaveTransformItem):
                if item.prevItem != self.allItems[i - 1]:
                    item.setPrevItem(self.allItems[i - 1])
                    changed.add(item)
                if i < len(self.allItems) - 1 and item.nextItem != self.allItems[i + 1]:
                    item.setNextItem(self.allItems[i + 1])
                    changed.add(item)
        if isinstance(item, WaveTransformItem) and item.nextItem != self.keyFrames[0]:
            item.setNextItem(self.keyFrames[0])
            changed.add(item)
        return changed

    def getUuidDict(self):
        return {item.uuid:item.index for item in self.keyFrames}

    def getSnapshot(self):
        content = []
        for item in self.allItems:
            if isinstance(item, SampleItem):
                content.append((item.uuid, self.index(item), item.values[:]))
            else:
                content.append((item.mode, deepcopy(item.data), item.prevWaveIndex))
        return content

    def setSnapshot(self, content):
        keyFrames = []
        fullList = [None for _ in range(64)]
        allItems = []
        prevItem = prevTransform = None
        for layoutIndex, itemData in enumerate(content):
            if isinstance(itemData[0], UUID):
                uuid, index, values = itemData
                item = SampleItem(self, uuid)
                keyFrames.append(item)
                fullList[index] = item
                self.fullValues[index] = values
                item.setWaveValues(zip(range(128), values))
                allItems.append(item)
                prevItem = item
                if prevTransform:
                    prevTransform.setNextItem(item)
            else:
                mode, data, prevWaveIndex = itemData
                prevTransform = WaveTransformItem(self, mode, prevItem, data=data)
                if not prevItem and prevWaveIndex is not None:
                    prevTransform.prevWaveIndex = prevWaveIndex
                allItems.append(prevTransform)
                prevItem = None
        self.keyFrames[:] = keyFrames
        self.fullList[:] = fullList
        #set cycle to last transform if no final keyFrame
        if isinstance(allItems[-1], WaveTransformItem):
            allItems[-1].setNextItem(keyFrames[0])
        #special case of restored layout with [SampleItem, WaveTransform, WaveTransform]
        if len(allItems) > 2:
            try:
                allItems[1].setNextItem(keyFrames[1])
            except:
                allItems[1].setNextItem(None)
        for item in self.allItems:
            #reset transforms before removal
            if isinstance(item, WaveTransformItem):
                item.setTargets(None, None)
            self.layout.removeItem(item)
            self.scene.removeItem(item)
            #important!!!
            del item
        self.allItems[:] = allItems
        for item in self.allItems:
            self.layout.addItem(item)
        self.scene.changed.emit()
        self.layout.invalidate()
        self.clean = False
        self.changed.emit()
#        print(', '.join([str(i) for i in allItems if isinstance(i, WaveTransformItem)]))

    def append(self, item):
        newIndex = self.index(self.keyFrames[-1]) + 1
        self.keyFrames.append(item)
        self.fullList[newIndex] = item
        transform = WaveTransformItem(self, 0, item)
        self.allItems.extend((item, transform))
#        item.indexChanged.connect(self.setFullDirty)
        item.changed.connect(self.setValuesDirty)
        self.clean = False
        self.layout.addItem(item)
        self.layout.addItem(transform)

    def extend(self, items):
        newIndex = self.index(self.keyFrames[-1]) + 1
        self.keyFrames.extend(items)
        for index, item in enumerate(items, newIndex):
            self.fullList[newIndex] = item
            transform = WaveTransformItem(self, item, 0)
            self.allItems.extend((item, transform))
            item.changed.connect(self.setValuesDirty)
        self.clean = False

#    def sort(self, *args, **kwargs):
#        self.keyFrames.sort(*args, **kwargs)
#        self.clean = False

    def pop(self, index):
        self.clean = False
        return self.keyFrames.pop(index)

    def __getitem__(self, index):
        return self.keyFrames[index]

    def __getslice__(self, start, end):
        return self.keyFrames[start:end]

    def __iter__(self):
        for keyFrame in self.keyFrames:
            yield keyFrame

    def __len__(self):
        return len(self.keyFrames)

    def fullTableValues(self, note, multiplier, sampleRate, index=None, reverse=False, export=False):
        if not export and note == self.currentNote and multiplier == self.multiplier and \
            self.clean and self.fullClean and self.fullAudioValues.any():
                return self.fullAudioValues
        if index is not None:
            if isinstance(index, int):
                #usa np.tile(array, multiplier)
                arrays = [np.concatenate((np.array(self.get(index).values), ) * 500)]
            else:
                arrays = [np.concatenate((np.array(index), ) * 500)]
        else:
#            arrays = [np.concatenate((np.array(self.keyFrames[0].values), ) * multiplier)]
            arrays = []
            iterFrames = iter(self.keyFrames)
            firstFrame = currentFrame = iterFrames.next()
            currentIndex = 0
            currentValues = self.fullValues[0]
            while True:
                try:
                    nextFrame = iterFrames.next()
                    nextIndex = nextFrame.index
                except:
                    nextFrame = firstFrame
                    nextIndex = 64
                if nextIndex != currentIndex + 1:
                    transform = currentFrame.nextTransform
#                    print('linear? {}'.format(transform.isLinear()))
#                    if not transform.mode:
                    if not transform.mode or not transform.isValid():
                        values = np.array(currentValues)
#                        arrays.append(np.concatenate((values, ) * (nextFrame.index - currentFrame.index - 1) * multiplier))
                        for _ in range(nextIndex - currentIndex):
                            arrays.append(np.concatenate((values, ) * multiplier))
                    elif transform.isLinear():
                        first = np.array(currentValues)
                        try:
                            last = np.array(self.fullValues[nextIndex])
                        except:
                            last = np.array(self.fullValues[0])
                        diff = (nextIndex - currentIndex)
                        ratio = 1. / diff
                        for index in range(diff):
                            percent = index * ratio
                            deltaArray = (1 - percent) * first + percent * last
                            arrays.append(np.concatenate((deltaArray, ) * multiplier))
                    elif transform.mode == WaveTransformItem.CurveMorph:
                        first = np.array(currentValues)
                        try:
                            last = np.array(self.fullValues[nextIndex])
                        except:
                            last = np.array(self.fullValues[0])
                        diff = (nextIndex - currentIndex)
                        ratio = 1. / diff
                        curveFunc = transform.curveFunction
                        for index in range(diff):
                            percent = curveFunc(index * ratio)
                            deltaArray = (1 - percent) * first + percent * last
                            arrays.append(np.concatenate((deltaArray, ) * multiplier))
                    elif transform.mode == WaveTransformItem.TransMorph:
                        first = np.array(currentValues)
                        try:
                            last = np.array(self.fullValues[nextIndex])
                        except:
                            last = np.array(self.fullValues[0])
                        diff = (nextIndex - currentIndex)
                        ratio = 1. / diff
                        offset = transform.translate
                        last = np.roll(last, offset)
                        for index in range(diff):
                            percent = index * ratio
                            deltaArray = np.roll((1 - percent) * first + percent * last, int(transform.translate * percent))
                            arrays.append(np.concatenate((deltaArray, ) * multiplier))
                    elif transform.mode == WaveTransformItem.SpecMorph:
                        first = np.array(currentValues)
                        try:
                            last = np.array(self.fullValues[nextIndex])
                        except:
                            last = np.array(self.fullValues[0])
                        diff = (nextIndex - currentIndex)
                        ratio = 1. / diff
                        harmonicsArrays = transform.getHarmonicsArray()
                        for index in range(diff):
                            percent = index * ratio
                            deltaArray = (1 - percent) * first + percent * last
                            np.clip(np.add(deltaArray, harmonicsArrays[index]), -pow20, pow20, out=deltaArray)
                            arrays.append(np.concatenate((deltaArray, ) * multiplier))
                else:
                    arrays.append(np.concatenate((np.array(currentValues), ) * multiplier))
#                arrays.append(np.concatenate((np.array(nextFrame.values), ) * multiplier))
                if nextIndex == 64:
                    break
                currentFrame = nextFrame
                currentIndex = self.index(currentFrame)
                currentValues = self.fullValues[currentIndex]
            if reverse:
                arrays += reversed(arrays)
#        array = np.array(self.fullValues) / float(pow22)
#        array = np.repeat(array, 2, axis=0)
#        data = np.concatenate((array, array), axis=1)

        if export:
            return arrays

        self.currentNote = note
        self.multiplier = multiplier

        noteRatio = sampleRate / 128. / noteFrequency(note) * 2

        base = np.concatenate(arrays) / float(pow22)
        fullRange = np.arange(len(base))
        count = np.arange(len(base) * noteRatio) / noteRatio

        self.fullAudioValues = np.interp(count, fullRange, base)
        waveRatio = float(len(self.fullAudioValues)) / len(base)
#        self.sampleRatio = noteFrequency(note) / multiplier
#        self.sampleRatio = (sampleRate / 128. / waveRatio * 2) / multiplier
#        print('diff', self.sampleRatio, noteFrequency(note) / multiplier)
        #this is an approximation :-(
        self.sampleRatio = ((sampleRate / 128. / waveRatio * 2) / multiplier) ** 2 / (noteFrequency(note) / multiplier)
        self.fullClean = True
        return self.fullAudioValues

class FakeObject(object):
    @property
    def changed(self):
        return FakeObject()

    addItem = removeItem = invalidate = emit = lambda *args: None


class FakeContainer(object):
    fakeObject = FakeObject()
    def layout(self):
        return self.fakeObject

    def scene(self):
        return self.fakeObject


class VirtualKeyFrames(KeyFrames):
    def __init__(self, snapshot):
        KeyFrames.__init__(self, FakeContainer())
        self.setSnapshot(snapshot)

from bigglesworth.wavetables.graphics import SampleItem, WaveTransformItem
