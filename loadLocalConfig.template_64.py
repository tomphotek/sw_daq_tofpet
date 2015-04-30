# -*- coding: utf-8 -*-
import atb
from atbUtils import loadAsicConfig, dumpAsicConfig, loadHVDACParams, loadBaseline

# Loads configuration for the local setup
def loadLocalConfig(useBaseline=True):
	atbConfig = atb.BoardConfig()
	# HV DAC calibration
	loadHVDACParams(atbConfig, "config/pab6/hvdac.Config")

	### Mezzanine A (J15) configuration
	loadAsicConfig(atbConfig, 0, 1, "config/FEBA/FEBA07/asic.config")
	if useBaseline:
		loadBaseline(atbConfig, 0, 1, "config/FEBA/FEBA07/asic.baseline");

	### Mezzanine B (J16) configuration
	loadAsicConfig(atbConfig, 2, 3, "config/FEBA/FEBA14/asic.config")
	if useBaseline:
		loadBaseline(atbConfig, 2, 3, "config/FEBA/FEBA14/asic.baseline");


	return atbConfig
	
