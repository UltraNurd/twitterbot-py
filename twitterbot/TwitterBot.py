# -*- coding: utf-8 -*-
"""
Configure and run threads that invoke event handlers.

Nicolas Ward
@ultranurd
ultranurd@yahoo.com
http://www.ultranurd.net/code/twitterbot/
2009.07.13
"""

"""
This file is part of Twitterbot.

Copyright © 2009, Nicolas Ward
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The term "Twitter" is Copyright © 2009 Twitter, Inc.
"""

# System includes
import sys
import os
import datetime
import time
import threading

# Twitter includes
import twitter

class TwitterBot(object):
    """
    Implement an event-handling polling-based Twitter metabot that uses
    callbacks to create a particular bot.

    This class can either be subclassed, or used generically with threadsafe
    callables passed in as event handlers.
    """

    def __init__(self, username, password, event_handlers = {}):
        """
        We need a Twitter user that this bot will run as.
        """

        # Store the Twitter credentials
        self.__api = twitter.Api(username, password)

        # Never cache (we want the bot to be responsive and non-duplicating)
        self.__api.SetCache(None)

        # Validate and store any initial callback callables
        self.__event_handlers = {}
        for eh_type, eh in event_handlers.iteritems():
            try:
                self.add_event_handlers(eh_type, *eh)
            except AttributeError:
                e_class, e, tb = sys.exc_info()
                ne = Exception("Invalid callback specified for %s" % eh_type)
                raise ne.__class__, ne, tb

        # We're not running until start() is called
        self.running = False

    def add_event_handler(self, type, callback, timeout = 15,
                          args = (), kwargs = {}):
        """
        Associate the specified callable (and optional arguments) with the
        specified callback type, assuming it's valid.
        """

        # Check for valid callback type
        if not hasattr(self, "_TwitterBot__thread_%s" % type):
            raise Exception("Invalid event handler type '%s'" % type)

        # Check for valid callable
        if not callable(callback):
            raise Exception("Callback is not callable")

        # Store the callback and its arguments as the handler for this event
        self.__event_handlers[type] = {"callback":callback,
                                       "timeout":timeout,
                                       "args":args,
                                       "kwargs":kwargs}

    def remove_event_handler(self, type):
        """
        Removes the specified event handler type (and stops any running thread).
        """

        # Tell this thread to stop, if necessary
        try:
            self.__locks[type].acquire()
            self.__running[type] = False
            self.__locks[type].release()
        except KeyError:
            pass

        # Remove the event handler for this type
        del self.__event_handlers[type]

    def __thread_get_dms(self):
        """
        Loop indefinitely, polling Twitter for direct messages sent to the bot's
        user.
        """

        # Determine the most recent DM as of startup (don't go into past)
        direct_messages = self.__api.GetDirectMessages()
        if len(direct_messages) > 0:
            # DMs come in reverse chronological order; first is most recent
            since_id = direct_messages[0].id
        else:
            since_id = 0

        # Get the event handler associated with this thread
        eh = self.__event_handlers["get_dms"]

        # Loop indefinitely
        while True:
            # Lock for the duration of this iteration
            self.__locks["get_dms"].acquire()

            # Check if we're stopping
            if not self.__running["get_dms"]:
                self.__locks["get_dms"].release()
                break

            # Read any new DMs received since last check
            direct_messages = self.__api.GetDirectMessages(since_id = since_id)

            # Process DMs in the order they were received, least recent 1st
            direct_messages.reverse()

            # Run the event handler on each DM received
            for direct_message in direct_messages:
                # Ignore any errors from the event handler
                try:
                    eh["callback"](self.__api, direct_message = direct_message,
                                   args = eh["args"], kwargs = eh["kwargs"])
                except Exception, e:
                    # Drop this DM on the floor and keep going
                    print "Could not process %s: %s" % (direct_message, e)
                    pass

            # Update the since filter based on the last DM read
            if len(direct_messages) > 0:
                # We reversed the list, so last is most recent
                since_id = direct_messages[-1].id

            # Done for this iteration
            self.__locks["get_dms"].release()

            # Wait until the appointed time, when the moon is lighting the pitch
            time.sleep(eh["timeout"])

    def __thread_get_replies(self):
        """
        Loop indefinitely, polling Twitter for replies sent to the bot's
        user.
        """

        # Determine the most recent reply as of startup (don't go into past)
        replies = self.__api.GetReplies()
        if len(replies) > 0:
            # Replies come in reverse chronological order; first is most recent
            since_id = replies[0].id
        else:
            since_id = 0

        # Get the event handler associated with this thread
        eh = self.__event_handlers["get_replies"]

        # Loop indefinitely
        while True:
            # Lock for the duration of this iteration
            self.__locks["get_replies"].acquire()

            # Check if we're stopping
            if not self.__running["get_replies"]:
                self.__locks["get_replies"].release()
                break

            # Read any new replies received since last check
            replies = self.__api.GetReplies(since_id = since_id)

            # Process replies in the order they were received, least recent 1st
            replies.reverse()

            # Run the event handler on each reply received
            for reply in replies:
                # Ignore any errors from the event handler
                try:
                    eh["callback"](self.__api, reply = reply,
                                   args = eh["args"], kwargs = eh["kwargs"])
                except Exception, e:
                    # Drop this reply on the floor and keep going
                    print "Could not process %s: %s" % (reply, e)
                    pass

            # Update the since filter based on the last reply read
            if len(replies) > 0:
                # We reversed the list, so last is most recent
                since_id = replies[-1].id

            # Done for this iteration
            self.__locks["get_replies"].release()

            # Wait until the appointed time, when the moon is lighting the pitch
            time.sleep(eh["timeout"])

    def __thread_get_timeline(self):
        """
        Loop indefinitely, polling Twitter for messages sent by those the bot
        account follows.
        """

        # Determine the most recent status as of startup (don't go into past)
        statuses = self.__api.GetFriendsTimeline()
        if len(statuses) > 0:
            # Statuses come in reverse chronological order; first is most recent
            since_id = statuses[0].id
        else:
            since_id = 0

        # Get the event handler associated with this thread
        eh = self.__event_handlers["get_timeline"]

        # Loop indefinitely
        while True:
            # Lock for the duration of this iteration
            self.__locks["get_timeline"].acquire()

            # Check if we're stopping
            if not self.__running["get_timeline"]:
                self.__locks["get_timeline"].release()
                break

            # Read any new statuses received since last check
            statuses = self.__api.GetFriendsTimeline(since_id = since_id)

            # Process statuses in the order they were received, least recent 1st
            statuses.reverse()

            # Run the event handler on each status posted by a friend
            for status in statuses:
                # Ignore any errors from the event handler
                try:
                    eh["callback"](self.__api, status = status,
                                   args = eh["args"], kwargs = eh["kwargs"])
                except Exception, e:
                    # Drop this friend's status on the floor and keep going
                    print "Could not process %s: %s" % (status, e)
                    pass

            # Update the since filter based on the last reply read
            if len(statuses) > 0:
                # We reversed the list, so last is most recent
                since_id = statuses[-1].id

            # Done for this iteration
            self.__locks["get_timeline"].release()

            # Wait until the appointed time, when the moon is lighting the pitch
            time.sleep(eh["timeout"])

    def start(self):
        """
        Initialize threads and locks for each defined event type and start them.
        """

        # Can only start once
        if self.running:
            return

        # Create a thread and a lock for each defined event handler
        self.__threads = {}
        self.__locks = {}
        self.__running = {}
        for eh_type in self.__event_handlers.keys():
            # Define this event handler's thread
            eh_method = getattr(self, "_TwitterBot__thread_%s" % eh_type)
            eh_threadname = "twbot_thread_%s" % eh_type
            self.__threads[eh_type] = threading.Thread(group = None,
                                                       target = eh_method,
                                                       name = eh_threadname)
            self.__locks[eh_type] = threading.RLock()
            self.__running[eh_type] = True

        # Start all the threads
        for thread in self.__threads.values():
            thread.start()

        # Running
        self.running = True

    def stop(self):
        """
        Tell all bot threads to stop and then wait for them to do so. This could
        take a while if one thread is mid-request.
        """

        # Can't stop if we haven't started
        if not self.running:
            return

        # Tell each thread to stop running
        for eh_type in self.__event_handlers.keys():
            self.__locks[eh_type].acquire()
            self.__running[eh_type] = False
            self.__locks[eh_type].release()

        # Wait for all threads to finish
        for thread in self.__threads.values():
            thread.join()

        # Stopped
        self.running = False
