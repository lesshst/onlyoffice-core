ICU_MAJOR_VER = 74

core_windows {
    exists($$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/icu) {
        INCLUDEPATH += $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/icu/include
    } else {
        build_xp {
            INCLUDEPATH += $$PWD/icu58/include
        } else {
            INCLUDEPATH += $$PWD/icu/include
        }
    }

    ICU_LIBS_PATH_WIN = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build
    build_xp {
        ICU_LIBS_PATH_WIN = $$ICU_LIBS_PATH_WIN/xp
    }
    LIBS        += -L$$ICU_LIBS_PATH_WIN -licuuc
}

core_linux {
    ICU_INCLUDE_DIR_LINUX = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build/include
    ICU_BUNDLED_LIBS_PATH_LINUX = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build
    ICU_ROOT_OVERRIDE = $$(OO_ICU_ROOT)

    isEmpty(ICU_ROOT_OVERRIDE):exists(/opt/oo-boost-1.74/include/unicode/utypes.h) {
        ICU_ROOT_OVERRIDE = /opt/oo-boost-1.74
    }

    !isEmpty(ICU_ROOT_OVERRIDE) {
        ICU_INCLUDE_DIR_LINUX = $${ICU_ROOT_OVERRIDE}/include
        LIBS += -L$${ICU_ROOT_OVERRIDE}/lib -licuuc -licudata -licui18n
    } else {
        INCLUDEPATH += $$ICU_INCLUDE_DIR_LINUX

        ICU_USE_SYSTEM_LIBS_LINUX = false
        exists(/usr/lib/aarch64-linux-gnu/libicuuc.so.$$ICU_MAJOR_VER):ICU_USE_SYSTEM_LIBS_LINUX = true
        exists(/usr/lib/x86_64-linux-gnu/libicuuc.so.$$ICU_MAJOR_VER):ICU_USE_SYSTEM_LIBS_LINUX = true
        exists(/usr/lib64/libicuuc.so.$$ICU_MAJOR_VER):ICU_USE_SYSTEM_LIBS_LINUX = true

        contains(ICU_USE_SYSTEM_LIBS_LINUX, true) {
            LIBS += -licuuc
            LIBS += -licudata
        } else {
            LIBS += $$ICU_BUNDLED_LIBS_PATH_LINUX/libicuuc.so.$$ICU_MAJOR_VER
            LIBS += $$ICU_BUNDLED_LIBS_PATH_LINUX/libicudata.so.$$ICU_MAJOR_VER
        }
    }

    INCLUDEPATH += $$ICU_INCLUDE_DIR_LINUX
}

core_mac {
    INCLUDEPATH += $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build/include

	ICU_LIBS_PATH_MAC = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build
	bundle_dylibs {
		LIBS	+= $$ICU_LIBS_PATH_MAC/libicudata.a
		LIBS	+= $$ICU_LIBS_PATH_MAC/libicui18n.a
		LIBS	+= $$ICU_LIBS_PATH_MAC/libicuuc.a
	} else {
		LIBS	+= $$ICU_LIBS_PATH_MAC/libicuuc.$${ICU_MAJOR_VER}.dylib
		LIBS	+= $$ICU_LIBS_PATH_MAC/libicudata.$${ICU_MAJOR_VER}.dylib
	}
}

core_ios {
    INCLUDEPATH += $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build/include

    ICU_LIBS_PATH_IOS = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build
    bundle_xcframeworks {
        xcframework_platform_ios_simulator {
            ICU_LIBS_PATH_IOS = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build_xc/simulator
        } else {
            ICU_LIBS_PATH_IOS = $$PWD/$$CORE_BUILDS_PLATFORM_PREFIX/build_xc
        }
    }

    LIBS += $$ICU_LIBS_PATH_IOS/libicudata.a
    LIBS += $$ICU_LIBS_PATH_IOS/libicui18n.a
    LIBS += $$ICU_LIBS_PATH_IOS/libicuuc.a
}

core_android {
    INCLUDEPATH += $$PWD/android/build/include

    LIBS        += $$PWD/android/build/$$CORE_BUILDS_PLATFORM_PREFIX_DST/libicuuc.a
    LIBS        += $$PWD/android/build/$$CORE_BUILDS_PLATFORM_PREFIX_DST/libicudata.a
}
