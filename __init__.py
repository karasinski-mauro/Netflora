
# -*- coding: utf-8 -*-
def classFactory(iface):
    from .plugin import NetfloraPlugin
    return NetfloraPlugin(iface)
