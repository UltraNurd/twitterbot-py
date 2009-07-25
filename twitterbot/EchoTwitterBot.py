#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A trivial example TwitterBot which echoes back any @mention or DM to the sender.

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
import re

# Twitterbot includes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import twitterbot

class EchoTwitterBot(twitterbot.TwitterBot):
    """
    Implement a simple example TwitterBot, with event handling methods for
    @mentions and DMs that immediately echo the contents back to the sender.
    """

    def __init__(self, username, password):
        """
        We need a Twitter user that this bot will run as.
        """

        # Create this TwitterBot
        super(EchoTwitterBot, self).__init__(username, password)

        # Add a callback for the DM and mention handlers
        self.add_event_handler("get_dms", self.__echo_dm)
        self.add_event_handler("get_replies", self.__echo_reply)

        # Prep a regular expression to filter this username out of replies
        self.re_reply = re.compile('^@%s\s*' % username)

    def __echo_dm(self, api, direct_message, args = (), kwargs = {}):
        """
        Reply to an incoming direct message by echoing the contents back
        to the sender.
        """

        # Echo their message back to them
        print "Received: %s" % direct_message
        posted = api.PostDirectMessage(direct_message.sender_id,
                                       direct_message.text)
        print "Sent: %s" % posted

    def __echo_reply(self, api, reply, args = (), kwargs = {}):
        """
        Reply to an incoming reply by echoing the contents back
        to the sender.
        """

        # Create a message to echo back to them
        print "Received: %s" % reply
        text = "@%s %s" % (reply.user.screen_name,
                           self.re_reply.sub("", reply.text))
        posted = api.PostUpdate(status = text, in_reply_to_status_id = reply.id)
        print "Sent: %s" % posted

def main():
    """
    Set up the bot and let it run.
    """

    # Check the command line arguments
    usage = "EchoTwitterBot.py <username> <password>"
    if len(sys.argv) != 3:
        print usage
        sys.exit(2)

    # Initialize the bot
    echo_bot = EchoTwitterBot(*sys.argv[1:])
    echo_bot.start()

    # Wait until EOF
    sys.stdin.read()

    # Stop the bot
    echo_bot.stop()

# Do not run on import
if __name__ == "__main__":
    main()
