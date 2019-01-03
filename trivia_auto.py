import requests
import json
from sopel.module import commands, example, NOLIMIT
import re
import random
from random import shuffle
from string import punctuation
import sys
if sys.version_info.major >= 3:
    unicode = str
    if sys.version_info.minor >= 4:
        from html import unescape
    else:
        from html.parser import HTMLParser
        unescape = HTMLParser().unescape
else:
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

'''
Python 2.7, with Python 3 hooks for unescape
Based on https://github.com/dasu/syrup-sopel-modules/blob/master/trivia.py
Python 3 unescape hook from : sopel/sopel/modules/reddit.py
Module stores Q/A to db with bot.nick. May not be the best for bots in multiple channels.
Special characters should be stripped from answers.
Jeopardy answers sometimes have <i> </i> that should be stripped out.
v 1.1: Fixed Score Clear Bug
v 1.2: .tt doesn't advance if there is a QA stored.
v 1.3: Added Jeopardy db from https://github.com/dasu/syrup-sopel-modules/blob/master/jeopardy.py
v 1.4: Added .a options? to give possible answers. Removed initial hint from trivia .
'''

@commands('trivia', 'tt')
def trivia(bot, trigger):
    if not bot.db.get_nick_value(bot.nick, 'trivia_status'): bot.db.set_nick_value(bot.nick, 'trivia_status', False)
    if trigger.group(2) == "on":
        bot.db.set_nick_value(bot.nick, 'trivia_status', True)
        bot.say("? for hint, ??? for answer, options? for options")
        get_trivia(bot)
    elif trigger.group(2) == "off": 
        bot.db.set_nick_value(bot.nick, 'trivia_status', False)
    elif bot.db.get_nick_value(bot.nick, 'trivia_answer'):
        bot.say(bot.db.get_nick_value(bot.nick, 'trivia_question'))
        bot.say("Answer: %s" % (re.sub('[a-zA-Z0-9]', '*', (bot.db.get_nick_value(bot.nick, 'trivia_answer')))))
    else: get_trivia(bot)

@commands('answer', 'a')
def trivia_answer(bot, trigger):
    check_values(bot, trigger.nick)
    guess = trigger.group(2)
    answer = bot.db.get_nick_value(bot.nick, 'trivia_answer')
    if answer: answer = answer.lstrip().rstrip().lower()
    if guess: guess = guess.lstrip().rstrip().lower()
    if guess == "help?": bot.say("? for hint, ??? for answer, options? for options" )
    elif guess == "options?": 
        options = bot.db.get_nick_value(bot.nick, "trivia_options")
        if not options: bot.say("No options found!")
        else: bot.say(options)
    elif not answer: bot.say("You need to ask a question!")
    elif not guess: 
        title = bot.db.get_nick_value(bot.nick, 'trivia_title')
        if title: bot.say("Category: %s" % (title))
        bot.say(bot.db.get_nick_value(bot.nick, 'trivia_question'))
        bot.say("Answer: %s" % (re.sub('[a-zA-Z0-9]', '*', answer)))
    elif guess == "?":
        hint = ""
        hintscale = bot.db.get_nick_value(bot.nick, 'trivia_hint_scale') - 8
        if hintscale == 80: hint = re.sub('[a-zA-Z0-9]', '*', (bot.db.get_nick_value(bot.nick, 'trivia_answer')))
        else:
            for x in answer:
                if not re.search('[a-zA-Z0-9]', x): hint += x
                elif random.randint(0,100) >= hintscale:    hint += x
                else:   hint += "*"
        bot.say(hint)
        bot.db.set_nick_value(bot.nick, 'trivia_hint_scale', hintscale)
        if hintscale < 80:
            hints = bot.db.get_nick_value(trigger.nick, 'trivia_hints')
            bot.db.set_nick_value(trigger.nick, 'trivia_hints', hints + 1)
        if hint == answer:
            bot.say("Hint gave the Answer.")
            bot.db.set_nick_value(bot.nick, 'trivia_answer', None)
            if bot.db.get_nick_value(bot.nick, 'trivia_status'): get_trivia(bot)
    elif guess == "???":
        bot.say(answer)
        bot.db.set_nick_value(bot.nick, 'trivia_answer', None)
        gives = bot.db.get_nick_value(trigger.nick, 'trivia_gives')
        bot.db.set_nick_value(trigger.nick, 'trivia_gives', gives + 1)
        if bot.db.get_nick_value(bot.nick, 'trivia_status'): get_trivia(bot)
    elif guess.lower() == answer:
        bot.say("Correct!")
        bot.db.set_nick_value(bot.nick, 'trivia_answer', None)
        score = bot.db.get_nick_value(trigger.nick, 'trivia_score')
        bot.db.set_nick_value(trigger.nick, 'trivia_score', score + 1)
        bot.say("%s has %d points!" % (trigger.nick, bot.db.get_nick_value(trigger.nick, 'trivia_score')))
        if bot.db.get_nick_value(bot.nick, 'trivia_status'): get_trivia(bot)
    else:
        bot.say("Nope!")
        wrong = bot.db.get_nick_value(trigger.nick, 'trivia_wrong')
        bot.db.set_nick_value(trigger.nick, 'trivia_wrong', wrong + 1)

@commands('score')
def trivia_score(bot, trigger):
    if trigger.group(2) and (len(trigger.group(2)) > 20): return
    if not trigger.group(2): nick = trigger.nick
    else: nick = trigger.group(2).lstrip().rstrip()
    if not bot.db.get_nick_value(nick, 'trivia_score'): bot.say("No Score")
    else:
        check_values(bot, nick)
        score = bot.db.get_nick_value(nick, 'trivia_score')
        wrong = bot.db.get_nick_value(nick, 'trivia_wrong')
        hints = bot.db.get_nick_value(nick, 'trivia_hints')
        gives = bot.db.get_nick_value(nick, 'trivia_gives')
        bot.say("%s has %d points, has had %d wrong answers, has used %d hints, and given up %d times!" % (nick, score, wrong, hints, gives))

def get_trivia(bot):
    source = random.randint(1,2)
    if source == 1: question, answer, title, hintscale, options = trivia_parser()
    if source == 2: question, answer, title, hintscale, options = jeopardy_parser()
    bot.db.set_nick_value(bot.nick, 'trivia_question', question)
    bot.db.set_nick_value(bot.nick, 'trivia_answer', answer)
    bot.db.set_nick_value(bot.nick, 'trivia_title', title)
    bot.db.set_nick_value(bot.nick, 'trivia_hint_scale', hintscale)
    bot.db.set_nick_value(bot.nick, 'trivia_options', options)
    starred_answer = re.sub('[a-zA-Z0-9]', '*', answer)
    if title: bot.say("Category: %s" % (title))
    bot.say(question)
    if source == 2: bot.say("Answer: %s" % (starred_answer))

def check_values(bot, nick):
    if not bot.db.get_nick_value(nick, 'trivia_score'): bot.db.set_nick_value(nick, 'trivia_score', 0)
    if not bot.db.get_nick_value(nick, 'trivia_wrong'): bot.db.set_nick_value(nick, 'trivia_wrong', 0)
    if not bot.db.get_nick_value(nick, 'trivia_hints'): bot.db.set_nick_value(nick, 'trivia_hints', 0)
    if not bot.db.get_nick_value(nick, 'trivia_gives'): bot.db.set_nick_value(nick, 'trivia_gives', 0)
    return

def trivia_parser():
    response = requests.get("https://opentdb.com/api.php?amount=1&type=multiple")
    data = response.json()
    g_question = data["results"][0]
    answer = unescape(g_question["correct_answer"]).lower()
    options = [g_question["correct_answer"],] + g_question["incorrect_answers"]
    shuffle(options)
    options = ", ".join(options)
    options = unescape(options)
    question = unescape(g_question["question"])
    return question, answer, None, 88, options

def jeopardy_parser():
    response = requests.get("http://jservice.io/api/random").json()
    question = response[0]['question']
    if not question or question == "": jeopardy_parser()
    else:
        answer = response[0]['answer'].lstrip().rstrip().lower()
        title = response[0]['category']['title'].title()
        return question, answer, title, 80, None
