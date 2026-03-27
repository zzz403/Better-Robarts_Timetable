-- UofT Study Rooms Launcher
-- This AppleScript creates a simple macOS app launcher

on run
    try
        -- Get the path to the app bundle
        set appPath to (path to me as string)
        set appFolder to appPath & "Contents:Resources:"
        
        -- Create the launch command
        set pythonScript to appFolder & "launcher.py"
        set launchCommand to "cd " & quoted form of (POSIX path of appFolder) & " && python3 launcher.py"
        
        -- Display startup message
        display notification "Starting UofT Study Rooms..." with title "Study Rooms"
        
        -- Launch the application
        do shell script launchCommand
        
    on error errMsg
        display dialog "Error launching UofT Study Rooms: " & errMsg buttons {"OK"} default button "OK" with icon stop
    end try
end run