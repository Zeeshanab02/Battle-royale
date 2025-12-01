[app]
title = FireClone Offline
package.name = fireclone
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1
requirements = python3,kivy==2.3.0,kivymd==2.0.0

[buildozer]
log_level = 2
warn_on_root = 1

android.permissions = INTERNET,VIBRATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 34
android.gradle_dependencies = 

android.add_src = src/android
android.add_aar = aar
android.enable_androidx = True
android.meta_data = com.google.android.gms.version=12451000

p4a.branch = master
