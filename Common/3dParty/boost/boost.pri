BOOST_INCLUDE_DIR = $$PWD/build/$$CORE_BUILDS_PLATFORM_PREFIX/include
CORE_BOOST_LIBS = $$PWD/build/$$CORE_BUILDS_PLATFORM_PREFIX/lib

BOOST_ROOT_OVERRIDE = $$(OO_BOOST_ROOT)
core_linux:isEmpty(BOOST_ROOT_OVERRIDE):exists(/opt/oo-boost-1.74/include/boost/version.hpp) {
    BOOST_ROOT_OVERRIDE = /opt/oo-boost-1.74
}

!isEmpty(BOOST_ROOT_OVERRIDE) {
    BOOST_INCLUDE_DIR = $${BOOST_ROOT_OVERRIDE}/include
    CORE_BOOST_LIBS = $${BOOST_ROOT_OVERRIDE}/lib
}

INCLUDEPATH += $$BOOST_INCLUDE_DIR

core_ios:CONFIG += disable_enum_constexpr_conversion
core_android:CONFIG += disable_enum_constexpr_conversion
core_mac:CONFIG += disable_enum_constexpr_conversion
core_linux_clang:CONFIG += disable_enum_constexpr_conversion

core_android {
    INCLUDEPATH += $$PWD/build/android/include
    CORE_BOOST_LIBS = $$PWD/build/android/lib/$$CORE_BUILDS_PLATFORM_PREFIX

    DEFINES += "_HAS_AUTO_PTR_ETC=0"
}

disable_enum_constexpr_conversion {
    QMAKE_CFLAGS += -Wno-enum-constexpr-conversion
    QMAKE_CXXFLAGS += -Wno-enum-constexpr-conversion
}

bundle_xcframeworks {
    xcframework_platform_ios_simulator {
        CORE_BOOST_LIBS = $$PWD/build/ios_xcframework/ios_simulator/lib/$$CORE_BUILDS_PLATFORM_PREFIX
    } else {
        CORE_BOOST_LIBS = $$PWD/build/ios_xcframework/ios/lib/$$CORE_BUILDS_PLATFORM_PREFIX
    }
}

core_win_arm64 {
    DEFINES += MICROSOFT_WINDOWS_WINBASE_H_DEFINE_INTERLOCKED_CPLUSPLUS_OVERLOADS=0
}

core_windows {
    VS_VERSION=140
    VS_DEBUG=
    VS_ARCH=x64
    core_debug:VS_DEBUG=gd-
    core_win_32:VS_ARCH=x32
    core_win_arm64:VS_ARCH=a64
    vs2019:VS_VERSION=142

    DEFINES += BOOST_USE_WINDOWS_H BOOST_WINAPI_NO_REDECLARATIONS

    BOOST_POSTFIX = -vc$${VS_VERSION}-mt-$${VS_DEBUG}$${VS_ARCH}-1_72

    core_boost_libs:LIBS += -L$$CORE_BOOST_LIBS -llibboost_system$$BOOST_POSTFIX -llibboost_filesystem$$BOOST_POSTFIX
    core_boost_regex:LIBS += -L$$CORE_BOOST_LIBS -llibboost_regex$$BOOST_POSTFIX
    core_boost_date_time:LIBS += -L$$CORE_BOOST_LIBS -llibboost_date_time$$BOOST_POSTFIX
} else {
    core_boost_libs:LIBS += -L$$CORE_BOOST_LIBS -lboost_system -lboost_filesystem
    core_boost_regex:LIBS += -L$$CORE_BOOST_LIBS -lboost_regex
    core_boost_date_time:LIBS += -L$$CORE_BOOST_LIBS -lboost_date_time
}
