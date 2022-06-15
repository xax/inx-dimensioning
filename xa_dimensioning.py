#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) XA [xa@antares.space], VI 2022. All rights reserved.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
"""
XA Dimensioning extension for Inkscape v1.2+.
"""

import inkex
import inkex.bezier
from inkex.localization import inkex_gettext as _
from math import sqrt

class XADimensioning(inkex.EffectExtension):
    """XA Measurements extension"""

    ## Interface implementation

    def add_arguments(self, pars):
        pars.add_argument("--tab", type=str, default="options")
        pars.add_argument(
            "-H",
            "--hide",
            type=inkex.Boolean,
            default=True,
            help="Hide dimensioned object after having been annotated",
        )
        pars.add_argument(
            "-p",
            "--perp",
            type=inkex.Boolean,
            default=False,
            help="Annotate un-closed paths perpendicularly",
        )
        pars.add_argument(
            "-L",
            "--linecolor",
            type=inkex.Color,
            default=inkex.Color(0xFFA500FF),
            help="Use document units instead of px",
        )
        pars.add_argument(
            "-u",
            "--useUU",
            type=inkex.Boolean,
            default=True,
            help="Use document units instead of px",
        )
        pars.add_argument(
            "-f",
            "--fontsize",
            type=int,
            default=10,
            help="Size of length label text in px",
        )
        pars.add_argument(
            "--xoffset",
            type=float,
            default=50.0,
            help="x offset of the vertical dimension arrow",
        )
        pars.add_argument(
            "--yoffset",
            type=float,
            default=50.0,
            help="y offset of the horizontal dimension arrow",
        )

    def effect(self):
        # configuration probably to be made accessable
        self._startOffset = 50
        self._sunit = self.svg.document_unit
        self._uuperunit = self.svg.unittouu("1" + self._sunit)  # convert to document units
        self._uuperpx = self.svg.unittouu("1px")  # convert px to document units
        #
        if not self.options.useUU:
            self.options.xoffset *= self._uuperpx
            self.options.yoffset *= self._uuperpx
            self.options.fontsize *= self._uuperpx

        layer = self.svg.get_current_layer()
        nodesPath = self.svg.selection.filter(inkex.PathElement)
        nodesRect = self.svg.selection.filter(inkex.Rectangle)
        if not nodesPath and not nodesRect:
            raise inkex.AbortExtension(_("Please select at least one path or rectangle object."))

        if nodesPath:
            if self.options.perp:
                for node in nodesPath:
                    self._annotatePathPerpendicularly(node, layer)
            else:
                for node in nodesPath:
                    self._annotatePath(node, layer)

        if nodesRect:
            for node in nodesRect:
                self._annotateRect(node, layer)

    ## Private implementation

    def _appendNewGroup(self, node, layer):
        group = inkex.Group()
        group.set("fill", None)
        group.set("stroke", self.options.linecolor)
        group.set(":xa-dimning", "group")
        group.label = node.eid + "-xa-dimning"
        group.href = node
        layer.append(group)
        return group

    def _annotatePathPerpendicularly(self, node, layer):

        # csp is a list of of segments, each a list of two+ control data triplets (incoming ctrl, point, outgoing ctrl)
        def csp_seg_reduce_bz(csp_seg, asp=0, bsp=-1):
            (spA, spB) = (csp_seg[asp], csp_seg[bsp])
            return (spA[1], spA[2], spB[0], spB[1])

        def csp_reduce_bz(csp, aseg=0, bseg=-1):
            (segA, segB) = (csp[aseg], csp[bseg])
            return (
                csp_seg_reduce_bz(segA, 0, 1),
                csp_seg_reduce_bz(segB, -2, -1)
            )

        csp = node.path.transform(node.composed_transform()).to_superpath()
        slengths, stotal = inkex.bezier.csplength(csp)
        bzA, bzB = csp_reduce_bz(csp)
        if bzA[0] == bzA[1]: # straight line, when point == control point
            ax = bzA[3][0] - bzA[0][0]
            ay = bzA[3][1] - bzA[0][1]
            scale = 1 / sqrt(ax**2 + ay**2)
            ax *= scale * self.options.xoffset
            ay *= scale * self.options.yoffset
        else:
            ax, ay = inkex.bezier.bezierslopeatt(bzA, 0.0) # slope at start[1] ((_c0, p0, d0), (c1, p1, d1), ...) of first[0] segment of csp
        if bzB[3] == bzB[2]:
            bx = bzB[3][0] - bzB[0][0]
            by = bzB[3][1] - bzB[0][1]
            scale = 1 / sqrt(bx**2 + by**2)
            bx *= scale * self.options.xoffset
            by *= scale * self.options.yoffset
        else:
            bx, by = inkex.bezier.bezierslopeatt(bzB, 1.0) # slope at end[-2] (..., (c2, p2, d2), (c1, p1, _d1)) of last[-1] segment of csp
        p0 = bzA[0] # csp[0][0][1] # start point of csp
        p1 = bzB[3] # csp[-1][-1][-2] # end point of csp
        q0 = (p0[0] + ay*.5, p0[1] - ax*.5)
        q1 = (p1[0] + by*.5, p1[1] - bx*.5)

        group = self._appendNewGroup(node, layer)
        line = inkex.PathElement()
        line.set("d", "M %f %f l %f %f" % (p0[0], p0[1], ay, -ax ))
        line.set("stroke-width", str(.5 * self._uuperpx))
        #line.set(":xa-debug", "ax=%f ay=%f bx=%f by=%f" % (ax, ay, bx, by))
        group.append(line)
        line = inkex.PathElement()
        line.set("d", "M %f %f l %f %f" % (p1[0], p1[1], by, -bx ))
        line.set("stroke-width", str(.5 * self._uuperpx))
        #line.set(":xa-debugA", "(%f, %f) (%f, %f) .. (%f, %f) (%f, %f)" % (bzA[0][0],bzA[0][1], bzA[1][0],bzA[1][1], bzA[2][0],bzA[2][1], bzA[3][0],bzA[3][1]))
        #line.set(":xa-debugB", "(%f, %f) (%f, %f) .. (%f, %f) (%f, %f)" % (bzB[0][0],bzB[0][1], bzB[1][0],bzB[1][1], bzB[2][0],bzB[2][1], bzB[3][0],bzB[3][1]))
        group.append(line)


        line = inkex.PathElement()
        line.set("d", "M %f %f L %f %f" % (q0[0], q0[1], q1[0], q1[1]))
        line.set("stroke-width", str(self._uuperpx))
        group.append(line)

        textElt = line.add(inkex.TextElement())
        textElt.set(":xa-dimning", "label")
        textElt.label = node.eid + "-xa-dimning-vert-dim"
        self._addText(node=textElt, dimVal=stotal, dx=ax*2, dy=ay*2, nodeHref=line, nodeRef=node, dimUnit=self._sunit)
        group.append(textElt)



    def _annotatePath(self, node, layer):
        bbox = node.bounding_box()
        dx = 0
        dy = 0

        group = self._appendNewGroup(node, layer)

        if bbox.width >= bbox.height:
            line = self._vert_line(bbox.left, [0, 2], bbox)
            line.set("stroke-width", str(.5 * self._uuperpx))
            line.label = node.eid + "-xa-dimning-horz-l"
            group.append(line)
            line = self._vert_line(bbox.right, [0, 2], bbox)
            line.set("stroke-width", str(.5 * self._uuperpx))
            line.label = node.eid + "-xa-dimning-horz-r"
            group.append(line)

            line = self._horz_line(bbox.top, [0, 1], bbox)
            line.set("stroke-width", str(self._uuperpx))
            line.label = node.eid + "-xa-dimning-horz"
            group.append(line)
            textElt = line.add(inkex.TextElement())
            textElt.set(":xa-dimning", "label")
            textElt.label = node.eid + "-xa-dimning-horz-dim"
            dy = 2
        else:
            line = self._horz_line(bbox.top, [2, 0], bbox)
            line.set("stroke-width", str(.5 * self._uuperpx))
            line.label = node.eid + "-xa-dimning-vert-t"
            group.append(line)
            line = self._horz_line(bbox.bottom, [2, 0], bbox)
            line.set("stroke-width", str(.5 * self._uuperpx))
            line.label = node.eid + "-xa-dimning-vert-b"
            group.append(line)

            line = self._vert_line(bbox.right, [-1, 0], bbox)
            line.set("stroke-width", str(self._uuperpx))
            line.label = node.eid + "-xa-dimning-vert"
            group.append(line)
            textElt = line.add(inkex.TextElement())
            textElt.set(":xa-dimning", "label")
            textElt.label = node.eid + "-xa-dimning-vert-dim"
            dx = 2

        self._addText(node=textElt, dimVal=bbox.height, dx=dx, dy=dy, nodeHref=line, nodeRef=node, dimUnit=self._sunit)
        group.append(textElt)

        if self.options.hide:
            node.style["display"] = "none"

    def _annotateRect(self, node, layer):
        bbox = node.bounding_box()

        group = self._appendNewGroup(node, layer)

        lineH = self._horz_line(bbox.top, [0, 1], bbox)
        lineH.set("stroke-width", str(self._uuperpx))
        lineH.label = node.eid + "-xa-dimning-horz"
        group.append(lineH)

        line = self._vert_line(bbox.left, [0, 2], bbox)
        line.set("stroke-width", str(.5 * self._uuperpx))
        line.label = node.eid + "-xa-dimning-horz-l"
        group.append(line)
        line = self._vert_line(bbox.right, [0, 2], bbox)
        line.set("stroke-width", str(.5 * self._uuperpx))
        line.label = node.eid + "-xa-dimning-horz-r"
        group.append(line)

        lineV = self._vert_line(bbox.right, [-1, 0], bbox)
        lineV.set("stroke-width", str(self._uuperpx))
        lineV.label = node.eid + "-xa-dimning-vert"
        group.append(lineV)

        line = self._horz_line(bbox.top, [2, 0], bbox)
        line.set("stroke-width", str(.5 * self._uuperpx))
        line.label = node.eid + "-xa-dimning-vert-t"
        group.append(line)
        line = self._horz_line(bbox.bottom, [2, 0], bbox)
        line.set("stroke-width", str(.5 * self._uuperpx))
        line.label = node.eid + "-xa-dimning-vert-b"
        group.append(line)

        textElt = lineH.add(inkex.TextElement())
        textElt.set(":xa-dimning", "label")
        textElt.label = node.eid + "-xa-dimning-horz-dim"
        self._addText(node=textElt, dimVal=bbox.width, dy=2, nodeHref=lineH, nodeRef=node, dimUnit=self._sunit)
        group.append(textElt)

        textElt = lineV.add(inkex.TextElement())
        textElt.set(":xa-dimning", "label")
        textElt.label = node.eid + "-xa-dimning-vert-dim"
        self._addText(node=textElt, dimVal=bbox.height, dx=2, nodeHref=lineV, nodeRef=node, dimUnit=self._sunit)
        group.append(textElt)

        if self.options.hide:
            node.style["display"] = "none"

    def _horz_line(self, y, xlat, bbox):
        """Create a horzontal line"""
        line = inkex.PathElement()
        x1 = bbox.left
        x2 = bbox.right + xlat[0] * self.options.xoffset
        y1 = y - xlat[1] * self.options.yoffset
        line.set("d", "M %f %f H %f" % (x1, y1, x2))
        return line

    def _vert_line(self, x, xlat, bbox):
        """Create a vertical line"""
        line = inkex.PathElement()
        x = x - xlat[0] * self.options.xoffset
        y1 = bbox.top - xlat[1] * self.options.yoffset
        y2 = bbox.bottom
        line.set("d", "M %f %f V %f" % (x, y1, y2))
        return line

    def _addText(self, node, dimVal, *, nodeHref, nodeRef=None, dx=0, dy=0, dimUnit=None):
        style = {
            "text-align": "center",
            "vertical-align": "bottom",
            "text-anchor": "start",
            "font-size": str(self.options.fontsize),
            "fill-opacity": "1.0",
            "stroke": "none",
            "font-weight": "normal",
            "font-style": "normal",
            "fill": self.options.linecolor,
        }
        newNode = inkex.TextPath()
        newNode.set(":xa-dimning", "text")
        if nodeRef is not None:
            newNode.set(":xa-dimning-ref", nodeRef.eid)
            newNode.label = nodeRef.eid + "-dim"
        newNode.set("startOffset", str(self._startOffset) + "%")
        if dy != 0:
            newNode.set("dy", str(-dy))
            newNode.set("dx", str(-nodeHref.bounding_box().width/2*self._uuperpx))
        if dx != 0:
            newNode.set("dy", str(-dx))
            newNode.set("dx", str(-nodeHref.bounding_box().height/2*self._uuperpx))
        newNode.style = style
        newNode.href = nodeHref
        #newNode.text = self.svg.add_unit(round(dimVal, 2), dimUnit)
        newNode.text = inkex.units.render_unit(round(dimVal, 2), dimUnit)
        node.add(newNode)


if __name__ == '__main__':
    XADimensioning().run()
