from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    EXCEPINFO, Default, IEnumVARIANT, OLE_XSIZE_PIXELS, Picture, Gray,
    OLE_XSIZE_HIMETRIC, OLE_YPOS_CONTAINER, HRESULT, CoClass,
    OLE_YPOS_PIXELS, OLE_COLOR, IPicture, OLE_XPOS_CONTAINER, Library,
    FONTSTRIKETHROUGH, Checked, FONTBOLD, OLE_XPOS_PIXELS,
    OLE_YSIZE_CONTAINER, Unchecked, FONTUNDERSCORE, VARIANT_BOOL,
    Monochrome, Color, IFontEventsDisp, IUnknown, BSTR, StdFont,
    DISPMETHOD, IFontDisp, OLE_YPOS_HIMETRIC, IPictureDisp, _lcid,
    FONTSIZE, OLE_YSIZE_PIXELS, FontEvents, VgaColor, DISPPARAMS,
    OLE_CANCELBOOL, _check_version, FONTITALIC, COMMETHOD, Font,
    OLE_HANDLE, IDispatch, StdPicture, OLE_ENABLEDEFAULTBOOL,
    typelib_path, FONTNAME, DISPPROPERTY, IFont, OLE_OPTEXCLUSIVE,
    OLE_XPOS_HIMETRIC, OLE_XSIZE_CONTAINER, dispid, GUID,
    OLE_YSIZE_HIMETRIC
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


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

