# -*- coding: mbcs -*-

from ctypes import *
from comtypes.automation import DISPPARAMS, EXCEPINFO, IDispatch, IEnumVARIANT
from comtypes import (
    _check_version, BSTR, CoClass, COMMETHOD, dispid, DISPMETHOD,
    DISPPROPERTY, GUID, IUnknown
)
from ctypes.wintypes import VARIANT_BOOL
from ctypes import HRESULT
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comtypes import hints


_lcid = 0  # change this if required
typelib_path = 'C:\\Windows\\System32\\stdole2.tlb'
OLE_YSIZE_CONTAINER = c_float
OLE_HANDLE = c_int
OLE_OPTEXCLUSIVE = VARIANT_BOOL
OLE_CANCELBOOL = VARIANT_BOOL
OLE_ENABLEDEFAULTBOOL = VARIANT_BOOL
OLE_XSIZE_HIMETRIC = c_int
OLE_YSIZE_HIMETRIC = c_int
OLE_XPOS_HIMETRIC = c_int
OLE_YPOS_HIMETRIC = c_int
FONTSIZE = c_longlong
OLE_XPOS_PIXELS = c_int
OLE_COLOR = c_ulong
FONTBOLD = VARIANT_BOOL
OLE_YPOS_PIXELS = c_int
FONTNAME = BSTR
OLE_XSIZE_PIXELS = c_int
FONTITALIC = VARIANT_BOOL
OLE_YSIZE_PIXELS = c_int
FONTUNDERSCORE = VARIANT_BOOL
FONTSTRIKETHROUGH = VARIANT_BOOL
OLE_XPOS_CONTAINER = c_float
OLE_XSIZE_CONTAINER = c_float
OLE_YPOS_CONTAINER = c_float

# values for enumeration 'OLE_TRISTATE'
Unchecked = 0
Checked = 1
Gray = 2
OLE_TRISTATE = c_int  # enum

# values for enumeration 'LoadPictureConstants'
Default = 0
Monochrome = 1
VgaColor = 2
Color = 4
LoadPictureConstants = c_int  # enum



class Font(IDispatch):
    _case_insensitive_ = True
    _iid_ = GUID('{BEF6E003-A874-101A-8BBA-00AA00300CAB}')
    _idlflags_ = []
    _methods_ = []

    if TYPE_CHECKING:  # dispmembers
        @property  # dispprop
        def Name(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Size(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Bold(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Italic(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Underline(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Strikethrough(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Weight(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Charset(self) -> hints.Incomplete: ...


Font._disp_methods_ = [
    DISPPROPERTY([dispid(0)], BSTR, 'Name'),
    DISPPROPERTY([dispid(2)], c_longlong, 'Size'),
    DISPPROPERTY([dispid(3)], VARIANT_BOOL, 'Bold'),
    DISPPROPERTY([dispid(4)], VARIANT_BOOL, 'Italic'),
    DISPPROPERTY([dispid(5)], VARIANT_BOOL, 'Underline'),
    DISPPROPERTY([dispid(6)], VARIANT_BOOL, 'Strikethrough'),
    DISPPROPERTY([dispid(7)], c_short, 'Weight'),
    DISPPROPERTY([dispid(8)], c_short, 'Charset'),
]


class Library(object):
    """OLE Automation"""
    name = 'stdole'
    _reg_typelib_ = ('{00020430-0000-0000-C000-000000000046}', 2, 0)


class Picture(IDispatch):
    _case_insensitive_ = True
    _iid_ = GUID('{7BF80981-BF32-101A-8BBB-00AA00300CAB}')
    _idlflags_ = []
    _methods_ = []

    if TYPE_CHECKING:  # dispmembers
        @property  # dispprop
        def Handle(self) -> hints.Incomplete: ...
        @property  # dispprop
        def hPal(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Type(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Width(self) -> hints.Incomplete: ...
        @property  # dispprop
        def Height(self) -> hints.Incomplete: ...
        def Render(self, hdc: hints.Incomplete, x: hints.Incomplete, y: hints.Incomplete, cx: hints.Incomplete, cy: hints.Incomplete, xSrc: hints.Incomplete, ySrc: hints.Incomplete, cxSrc: hints.Incomplete, cySrc: hints.Incomplete, prcWBounds: hints.Incomplete) -> hints.Incomplete: ...


Picture._disp_methods_ = [
    DISPPROPERTY([dispid(0), 'readonly'], OLE_HANDLE, 'Handle'),
    DISPPROPERTY([dispid(2)], OLE_HANDLE, 'hPal'),
    DISPPROPERTY([dispid(3), 'readonly'], c_short, 'Type'),
    DISPPROPERTY([dispid(4), 'readonly'], OLE_XSIZE_HIMETRIC, 'Width'),
    DISPPROPERTY([dispid(5), 'readonly'], OLE_YSIZE_HIMETRIC, 'Height'),
    DISPMETHOD(
        [dispid(6)],
        None,
        'Render',
        ([], c_int, 'hdc'),
        ([], c_int, 'x'),
        ([], c_int, 'y'),
        ([], c_int, 'cx'),
        ([], c_int, 'cy'),
        ([], OLE_XPOS_HIMETRIC, 'xSrc'),
        ([], OLE_YPOS_HIMETRIC, 'ySrc'),
        ([], OLE_XSIZE_HIMETRIC, 'cxSrc'),
        ([], OLE_YSIZE_HIMETRIC, 'cySrc'),
        ([], c_void_p, 'prcWBounds')
    ),
]
IPictureDisp = Picture


class StdPicture(CoClass):
    _reg_clsid_ = GUID('{0BE35204-8F91-11CE-9DE3-00AA004BB851}')
    _idlflags_ = []
    _typelib_path_ = typelib_path
    _reg_typelib_ = ('{00020430-0000-0000-C000-000000000046}', 2, 0)


class IPicture(IUnknown):
    """Picture Object"""
    _case_insensitive_ = True
    _iid_ = GUID('{7BF80980-BF32-101A-8BBB-00AA00300CAB}')
    _idlflags_ = ['hidden']

    if TYPE_CHECKING:  # commembers
        def _get_Handle(self) -> hints.Incomplete: ...
        Handle = hints.normal_property(_get_Handle)
        def _get_hPal(self) -> hints.Incomplete: ...
        def _set_hPal(self, phpal: hints.Incomplete) -> hints.Hresult: ...
        hPal = hints.normal_property(_get_hPal, _set_hPal)
        def _get_Type(self) -> hints.Incomplete: ...
        Type = hints.normal_property(_get_Type)
        def _get_Width(self) -> hints.Incomplete: ...
        Width = hints.normal_property(_get_Width)
        def _get_Height(self) -> hints.Incomplete: ...
        Height = hints.normal_property(_get_Height)
        def Render(self, hdc: hints.Incomplete, x: hints.Incomplete, y: hints.Incomplete, cx: hints.Incomplete, cy: hints.Incomplete, xSrc: hints.Incomplete, ySrc: hints.Incomplete, cxSrc: hints.Incomplete, cySrc: hints.Incomplete, prcWBounds: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurDC(self) -> hints.Incomplete: ...
        CurDC = hints.normal_property(_get_CurDC)
        def SelectPicture(self, hdcIn: hints.Incomplete) -> hints.Tuple[hints.Incomplete, hints.Incomplete]: ...
        def _get_KeepOriginalFormat(self) -> hints.Incomplete: ...
        def _set_KeepOriginalFormat(self, pfkeep: hints.Incomplete) -> hints.Hresult: ...
        KeepOriginalFormat = hints.normal_property(_get_KeepOriginalFormat, _set_KeepOriginalFormat)
        def PictureChanged(self) -> hints.Hresult: ...
        def SaveAsFile(self, pstm: hints.Incomplete, fSaveMemCopy: hints.Incomplete) -> hints.Incomplete: ...
        def _get_Attributes(self) -> hints.Incomplete: ...
        Attributes = hints.normal_property(_get_Attributes)
        def SetHdc(self, hdc: hints.Incomplete) -> hints.Hresult: ...


StdPicture._com_interfaces_ = [Picture, IPicture]
IFontDisp = Font

IPicture._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Handle',
        (['out', 'retval'], POINTER(OLE_HANDLE), 'phandle')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'hPal',
        (['out', 'retval'], POINTER(OLE_HANDLE), 'phpal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Type',
        (['out', 'retval'], POINTER(c_short), 'ptype')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Width',
        (['out', 'retval'], POINTER(OLE_XSIZE_HIMETRIC), 'pwidth')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Height',
        (['out', 'retval'], POINTER(OLE_YSIZE_HIMETRIC), 'pheight')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Render',
        (['in'], c_int, 'hdc'),
        (['in'], c_int, 'x'),
        (['in'], c_int, 'y'),
        (['in'], c_int, 'cx'),
        (['in'], c_int, 'cy'),
        (['in'], OLE_XPOS_HIMETRIC, 'xSrc'),
        (['in'], OLE_YPOS_HIMETRIC, 'ySrc'),
        (['in'], OLE_XSIZE_HIMETRIC, 'cxSrc'),
        (['in'], OLE_YSIZE_HIMETRIC, 'cySrc'),
        (['in'], c_void_p, 'prcWBounds')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'hPal',
        (['in'], OLE_HANDLE, 'phpal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurDC',
        (['out', 'retval'], POINTER(c_int), 'phdcOut')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SelectPicture',
        (['in'], c_int, 'hdcIn'),
        (['out'], POINTER(c_int), 'phdcOut'),
        (['out'], POINTER(OLE_HANDLE), 'phbmpOut')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'KeepOriginalFormat',
        (['out', 'retval'], POINTER(VARIANT_BOOL), 'pfkeep')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'KeepOriginalFormat',
        (['in'], VARIANT_BOOL, 'pfkeep')
    ),
    COMMETHOD([], HRESULT, 'PictureChanged'),
    COMMETHOD(
        [],
        HRESULT,
        'SaveAsFile',
        (['in'], c_void_p, 'pstm'),
        (['in'], VARIANT_BOOL, 'fSaveMemCopy'),
        (['out'], POINTER(c_int), 'pcbSize')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Attributes',
        (['out', 'retval'], POINTER(c_int), 'pdwAttr')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetHdc',
        (['in'], OLE_HANDLE, 'hdc')
    ),
]

################################################################
# code template for IPicture implementation
# class IPicture_Impl(object):
#     @property
#     def Handle(self):
#         '-no docstring-'
#         #return phandle
#
#     def _get(self):
#         '-no docstring-'
#         #return phpal
#     def _set(self, phpal):
#         '-no docstring-'
#     hPal = property(_get, _set, doc = _set.__doc__)
#
#     @property
#     def Type(self):
#         '-no docstring-'
#         #return ptype
#
#     @property
#     def Width(self):
#         '-no docstring-'
#         #return pwidth
#
#     @property
#     def Height(self):
#         '-no docstring-'
#         #return pheight
#
#     def Render(self, hdc, x, y, cx, cy, xSrc, ySrc, cxSrc, cySrc, prcWBounds):
#         '-no docstring-'
#         #return 
#
#     @property
#     def CurDC(self):
#         '-no docstring-'
#         #return phdcOut
#
#     def SelectPicture(self, hdcIn):
#         '-no docstring-'
#         #return phdcOut, phbmpOut
#
#     def _get(self):
#         '-no docstring-'
#         #return pfkeep
#     def _set(self, pfkeep):
#         '-no docstring-'
#     KeepOriginalFormat = property(_get, _set, doc = _set.__doc__)
#
#     def PictureChanged(self):
#         '-no docstring-'
#         #return 
#
#     def SaveAsFile(self, pstm, fSaveMemCopy):
#         '-no docstring-'
#         #return pcbSize
#
#     @property
#     def Attributes(self):
#         '-no docstring-'
#         #return pdwAttr
#
#     def SetHdc(self, hdc):
#         '-no docstring-'
#         #return 
#


class StdFont(CoClass):
    _reg_clsid_ = GUID('{0BE35203-8F91-11CE-9DE3-00AA004BB851}')
    _idlflags_ = []
    _typelib_path_ = typelib_path
    _reg_typelib_ = ('{00020430-0000-0000-C000-000000000046}', 2, 0)


class FontEvents(IDispatch):
    """Event interface for the Font object"""
    _case_insensitive_ = True
    _iid_ = GUID('{4EF6100A-AF88-11D0-9846-00C04FC29993}')
    _idlflags_ = ['hidden']
    _methods_ = []

    if TYPE_CHECKING:  # dispmembers
        def FontChanged(self, PropertyName: hints.Incomplete) -> hints.Incomplete: ...


class IFont(IUnknown):
    """Font Object"""
    _case_insensitive_ = True
    _iid_ = GUID('{BEF6E002-A874-101A-8BBA-00AA00300CAB}')
    _idlflags_ = ['hidden']

    if TYPE_CHECKING:  # commembers
        def _get_Name(self) -> hints.Incomplete: ...
        def _set_Name(self, pname: hints.Incomplete) -> hints.Hresult: ...
        Name = hints.normal_property(_get_Name, _set_Name)
        def _get_Size(self) -> hints.Incomplete: ...
        def _set_Size(self, psize: hints.Incomplete) -> hints.Hresult: ...
        Size = hints.normal_property(_get_Size, _set_Size)
        def _get_Bold(self) -> hints.Incomplete: ...
        def _set_Bold(self, pbold: hints.Incomplete) -> hints.Hresult: ...
        Bold = hints.normal_property(_get_Bold, _set_Bold)
        def _get_Italic(self) -> hints.Incomplete: ...
        def _set_Italic(self, pitalic: hints.Incomplete) -> hints.Hresult: ...
        Italic = hints.normal_property(_get_Italic, _set_Italic)
        def _get_Underline(self) -> hints.Incomplete: ...
        def _set_Underline(self, punderline: hints.Incomplete) -> hints.Hresult: ...
        Underline = hints.normal_property(_get_Underline, _set_Underline)
        def _get_Strikethrough(self) -> hints.Incomplete: ...
        def _set_Strikethrough(self, pstrikethrough: hints.Incomplete) -> hints.Hresult: ...
        Strikethrough = hints.normal_property(_get_Strikethrough, _set_Strikethrough)
        def _get_Weight(self) -> hints.Incomplete: ...
        def _set_Weight(self, pweight: hints.Incomplete) -> hints.Hresult: ...
        Weight = hints.normal_property(_get_Weight, _set_Weight)
        def _get_Charset(self) -> hints.Incomplete: ...
        def _set_Charset(self, pcharset: hints.Incomplete) -> hints.Hresult: ...
        Charset = hints.normal_property(_get_Charset, _set_Charset)
        def _get_hFont(self) -> hints.Incomplete: ...
        hFont = hints.normal_property(_get_hFont)
        def Clone(self) -> 'IFont': ...
        def IsEqual(self, pfontOther: hints.Incomplete) -> hints.Hresult: ...
        def SetRatio(self, cyLogical: hints.Incomplete, cyHimetric: hints.Incomplete) -> hints.Hresult: ...
        def AddRefHfont(self, hFont: hints.Incomplete) -> hints.Hresult: ...
        def ReleaseHfont(self, hFont: hints.Incomplete) -> hints.Hresult: ...


StdFont._com_interfaces_ = [Font, IFont]
StdFont._outgoing_interfaces_ = [FontEvents]

FontEvents._disp_methods_ = [
    DISPMETHOD(
        [dispid(9)],
        None,
        'FontChanged',
        (['in'], BSTR, 'PropertyName')
    ),
]

IFont._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Name',
        (['out', 'retval'], POINTER(BSTR), 'pname')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Name',
        (['in'], BSTR, 'pname')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Size',
        (['out', 'retval'], POINTER(c_longlong), 'psize')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Size',
        (['in'], c_longlong, 'psize')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Bold',
        (['out', 'retval'], POINTER(VARIANT_BOOL), 'pbold')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Bold',
        (['in'], VARIANT_BOOL, 'pbold')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Italic',
        (['out', 'retval'], POINTER(VARIANT_BOOL), 'pitalic')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Italic',
        (['in'], VARIANT_BOOL, 'pitalic')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Underline',
        (['out', 'retval'], POINTER(VARIANT_BOOL), 'punderline')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Underline',
        (['in'], VARIANT_BOOL, 'punderline')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Strikethrough',
        (['out', 'retval'], POINTER(VARIANT_BOOL), 'pstrikethrough')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Strikethrough',
        (['in'], VARIANT_BOOL, 'pstrikethrough')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Weight',
        (['out', 'retval'], POINTER(c_short), 'pweight')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Weight',
        (['in'], c_short, 'pweight')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Charset',
        (['out', 'retval'], POINTER(c_short), 'pcharset')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'Charset',
        (['in'], c_short, 'pcharset')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'hFont',
        (['out', 'retval'], POINTER(OLE_HANDLE), 'phfont')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Clone',
        (['out'], POINTER(POINTER(IFont)), 'ppfont')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'IsEqual',
        (['in'], POINTER(IFont), 'pfontOther')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetRatio',
        (['in'], c_int, 'cyLogical'),
        (['in'], c_int, 'cyHimetric')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddRefHfont',
        (['in'], OLE_HANDLE, 'hFont')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ReleaseHfont',
        (['in'], OLE_HANDLE, 'hFont')
    ),
]

################################################################
# code template for IFont implementation
# class IFont_Impl(object):
#     def _get(self):
#         '-no docstring-'
#         #return pname
#     def _set(self, pname):
#         '-no docstring-'
#     Name = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return psize
#     def _set(self, psize):
#         '-no docstring-'
#     Size = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return pbold
#     def _set(self, pbold):
#         '-no docstring-'
#     Bold = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return pitalic
#     def _set(self, pitalic):
#         '-no docstring-'
#     Italic = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return punderline
#     def _set(self, punderline):
#         '-no docstring-'
#     Underline = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return pstrikethrough
#     def _set(self, pstrikethrough):
#         '-no docstring-'
#     Strikethrough = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return pweight
#     def _set(self, pweight):
#         '-no docstring-'
#     Weight = property(_get, _set, doc = _set.__doc__)
#
#     def _get(self):
#         '-no docstring-'
#         #return pcharset
#     def _set(self, pcharset):
#         '-no docstring-'
#     Charset = property(_get, _set, doc = _set.__doc__)
#
#     @property
#     def hFont(self):
#         '-no docstring-'
#         #return phfont
#
#     def Clone(self):
#         '-no docstring-'
#         #return ppfont
#
#     def IsEqual(self, pfontOther):
#         '-no docstring-'
#         #return 
#
#     def SetRatio(self, cyLogical, cyHimetric):
#         '-no docstring-'
#         #return 
#
#     def AddRefHfont(self, hFont):
#         '-no docstring-'
#         #return 
#
#     def ReleaseHfont(self, hFont):
#         '-no docstring-'
#         #return 
#
IFontEventsDisp = FontEvents

__all__ = [
    'FONTSIZE', 'OLE_YSIZE_PIXELS', 'Default', 'OLE_XSIZE_PIXELS',
    'Picture', 'FontEvents', 'Gray', 'OLE_XSIZE_HIMETRIC', 'VgaColor',
    'OLE_YPOS_CONTAINER', 'OLE_YPOS_PIXELS', 'OLE_COLOR', 'IPicture',
    'OLE_CANCELBOOL', 'OLE_XPOS_CONTAINER', 'Library',
    'FONTSTRIKETHROUGH', 'FONTITALIC', 'Checked', 'Font',
    'OLE_HANDLE', 'FONTBOLD', 'OLE_XPOS_PIXELS', 'StdPicture',
    'OLE_YSIZE_CONTAINER', 'OLE_ENABLEDEFAULTBOOL', 'IFontDisp',
    'typelib_path', 'Unchecked', 'LoadPictureConstants', 'FONTNAME',
    'OLE_TRISTATE', 'FONTUNDERSCORE', 'IFont', 'Monochrome', 'Color',
    'IFontEventsDisp', 'OLE_OPTEXCLUSIVE', 'OLE_XPOS_HIMETRIC',
    'OLE_XSIZE_CONTAINER', 'StdFont', 'OLE_YSIZE_HIMETRIC',
    'OLE_YPOS_HIMETRIC', 'IPictureDisp'
]

_check_version('1.4.8', 1651900738.765207)
