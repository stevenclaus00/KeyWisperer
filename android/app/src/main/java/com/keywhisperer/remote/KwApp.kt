package com.keywhisperer.remote

import android.app.Application

/** Runs once per process: sets up the shared [Session]. */
class KwApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Session.init(this)
    }
}
