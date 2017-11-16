"""
Simple turn-based combat system with items and status effects

Contrib - Tim Ashley Jenkins 2017

This is a version of the 'turnbattle' combat system that includes status
effects and usable items, which can instill these status effects, cure
them, or do just about anything else.

Status effects are stored on characters as a dictionary, where the key
is the name of the status effect and the value is a list of two items:
an integer representing the number of turns left until the status runs
out, and the character upon whose turn the condition timer is ticked
down. Unlike most combat-related attributes, conditions aren't wiped
once combat ends - if out of combat, they tick down in real time
instead. 

Items aren't given any sort of special typeclass - instead, whether or
not an object counts as an item is determined by its attributes. To make
an object into an item, it must have the attribute 'item_on_use', with
the value given as a callable - this is the function that will be called
when an item is used. Other properties of the item, such as how many
uses it has, whether it's destroyed when its uses are depleted, and such
can be specified on the item as well, but they are optional.

To install and test, import this module's TBItemsCharacter object into
your game's character.py module:

    from evennia.contrib.turnbattle.tb_items import TBItemsCharacter

And change your game's character typeclass to inherit from TBItemsCharacter
instead of the default:

    class Character(TBItemsCharacter):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.turnbattle import tb_items

And add the battle command set to your default command set:

    #
    # any commands you add below will overload the default ones.
    #
    self.add(tb_items.BattleCmdSet())

This module is meant to be heavily expanded on, so you may want to copy it
to your game's 'world' folder and modify it there rather than importing it
in your game and using it as-is.
"""

from random import randint
from evennia import DefaultCharacter, Command, default_cmds, DefaultScript
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default.help import CmdHelp
from evennia.utils.spawner import spawn

"""
----------------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------------
"""

TURN_TIMEOUT = 30 # Time before turns automatically end, in seconds
ACTIONS_PER_TURN = 1 # Number of actions allowed per turn

"""
----------------------------------------------------------------------------
COMBAT FUNCTIONS START HERE
----------------------------------------------------------------------------
"""

def roll_init(character):
    """
    Rolls a number between 1-1000 to determine initiative.

    Args:
        character (obj): The character to determine initiative for

    Returns:
        initiative (int): The character's place in initiative - higher
        numbers go first.

    Notes:
        By default, does not reference the character and simply returns
        a random integer from 1 to 1000.

        Since the character is passed to this function, you can easily reference
        a character's stats to determine an initiative roll - for example, if your
        character has a 'dexterity' attribute, you can use it to give that character
        an advantage in turn order, like so:

        return (randint(1,20)) + character.db.dexterity

        This way, characters with a higher dexterity will go first more often.
    """
    return randint(1, 1000)


def get_attack(attacker, defender):
    """
    Returns a value for an attack roll.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Returns:
        attack_value (int): Attack roll value, compared against a defense value
            to determine whether an attack hits or misses.

    Notes:
        By default, returns a random integer from 1 to 100 without using any
        properties from either the attacker or defender.

        This can easily be expanded to return a value based on characters stats,
        equipment, and abilities. This is why the attacker and defender are passed
        to this function, even though nothing from either one are used in this example.
    """
    # For this example, just return a random integer up to 100.
    attack_value = randint(1, 100)
    return attack_value


def get_defense(attacker, defender):
    """
    Returns a value for defense, which an attack roll must equal or exceed in order
    for an attack to hit.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Returns:
        defense_value (int): Defense value, compared against an attack roll
            to determine whether an attack hits or misses.

    Notes:
        By default, returns 50, not taking any properties of the defender or
        attacker into account.

        As above, this can be expanded upon based on character stats and equipment.
    """
    # For this example, just return 50, for about a 50/50 chance of hit.
    defense_value = 50
    return defense_value


def get_damage(attacker, defender):
    """
    Returns a value for damage to be deducted from the defender's HP after abilities
    successful hit.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being damaged

    Returns:
        damage_value (int): Damage value, which is to be deducted from the defending
            character's HP.

    Notes:
        By default, returns a random integer from 15 to 25 without using any
        properties from either the attacker or defender.

        Again, this can be expanded upon.
    """
    # For this example, just generate a number between 15 and 25.
    damage_value = randint(15, 25)
    return damage_value


def apply_damage(defender, damage):
    """
    Applies damage to a target, reducing their HP by the damage amount to a
    minimum of 0.

    Args:
        defender (obj): Character taking damage
        damage (int): Amount of damage being taken
    """
    defender.db.hp -= damage  # Reduce defender's HP by the damage dealt.
    # If this reduces it to 0 or less, set HP to 0.
    if defender.db.hp <= 0:
        defender.db.hp = 0

def at_defeat(defeated):
    """
    Announces the defeat of a fighter in combat.
    
    Args:
        defeated (obj): Fighter that's been defeated.
    
    Notes:
        All this does is announce a defeat message by default, but if you
        want anything else to happen to defeated fighters (like putting them
        into a dying state or something similar) then this is the place to
        do it.
    """
    defeated.location.msg_contents("%s has been defeated!" % defeated)

def resolve_attack(attacker, defender, attack_value=None, defense_value=None, damage_value=None):
    """
    Resolves an attack and outputs the result.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Notes:
        Even though the attack and defense values are calculated
        extremely simply, they are separated out into their own functions
        so that they are easier to expand upon.
    """
    # Get an attack roll from the attacker.
    if not attack_value:
        attack_value = get_attack(attacker, defender)
    # Get a defense value from the defender.
    if not defense_value:
        defense_value = get_defense(attacker, defender)
    # If the attack value is lower than the defense value, miss. Otherwise, hit.
    if attack_value < defense_value:
        attacker.location.msg_contents("%s's attack misses %s!" % (attacker, defender))
    else:
        if not damage_value:
            damage_value = get_damage(attacker, defender)  # Calculate damage value.
        # Announce damage dealt and apply damage.
        attacker.location.msg_contents("%s hits %s for %i damage!" % (attacker, defender, damage_value))
        apply_damage(defender, damage_value)
        # If defender HP is reduced to 0 or less, call at_defeat.
        if defender.db.hp <= 0:
            at_defeat(defender)

def combat_cleanup(character):
    """
    Cleans up all the temporary combat-related attributes on a character.

    Args:
        character (obj): Character to have their combat attributes removed

    Notes:
        Any attribute whose key begins with 'combat_' is temporary and no
        longer needed once a fight ends.
    """
    for attr in character.attributes.all():
        if attr.key[:7] == "combat_":  # If the attribute name starts with 'combat_'...
            character.attributes.remove(key=attr.key)  # ...then delete it!


def is_in_combat(character):
    """
    Returns true if the given character is in combat.

    Args:
        character (obj): Character to determine if is in combat or not

    Returns:
        (bool): True if in combat or False if not in combat
    """
    return bool(character.db.combat_turnhandler)


def is_turn(character):
    """
    Returns true if it's currently the given character's turn in combat.

    Args:
        character (obj): Character to determine if it is their turn or not

    Returns:
        (bool): True if it is their turn or False otherwise
    """
    turnhandler = character.db.combat_turnhandler
    currentchar = turnhandler.db.fighters[turnhandler.db.turn]
    return bool(character == currentchar)


def spend_action(character, actions, action_name=None):
    """
    Spends a character's available combat actions and checks for end of turn.

    Args:
        character (obj): Character spending the action
        actions (int) or 'all': Number of actions to spend, or 'all' to spend all actions

    Kwargs:
        action_name (str or None): If a string is given, sets character's last action in
        combat to provided string
    """
    if action_name:
        character.db.combat_lastaction = action_name
    if actions == 'all':  # If spending all actions
        character.db.combat_actionsleft = 0  # Set actions to 0
    else:
        character.db.combat_actionsleft -= actions  # Use up actions.
        if character.db.combat_actionsleft < 0:
            character.db.combat_actionsleft = 0  # Can't have fewer than 0 actions
    character.db.combat_turnhandler.turn_end_check(character)  # Signal potential end of turn.

def spend_item_use(item):
    """
    Spends one use on an item with limited uses. If item.db.item_consumable
    is 'True', the item is destroyed if it runs out of uses - if it's a string
    instead of 'True', it will also spawn a new object as residue, using the
    value of item.db.item_consumable as the name of the prototype to spawn.
    
    
    """
    if item.db.item_uses:
        item.db.item_uses -= 1 # Spend one use
        if item.db.item_uses > 0: # Has uses remaining
            # Inform th eplayer
            self.caller.msg("%s has %i uses remaining." % (item.key.capitalize(), item.db.item_uses))
        else: # All uses spent
            if not item.db.item_consumable:
                # If not consumable, just inform the player that the uses are gone
                self.caller.msg("%s has no uses remaining." % item.key.capitalize())
            else: # If consumable
                if item.db.item_consumable == True: # If the value is 'True', just destroy the item
                    self.caller.msg("%s has been consumed." % item.key.capitalize())
                    item.delete() # Delete the spent item
                else: # If a string, use value of item_consumable to spawn an object in its place
                    residue = spawn({"prototype":item.db.item_consumable})[0] # Spawn the residue
                    residue.location = item.location # Move the residue to the same place as the item
                    self.caller.msg("After using %s, you are left with %s." % (item, residue))
                    item.delete() # Delete the spent item

"""
----------------------------------------------------------------------------
CHARACTER TYPECLASS
----------------------------------------------------------------------------
"""


class TBItemsCharacter(DefaultCharacter):
    """
    A character able to participate in turn-based combat. Has attributes for current
    and maximum HP, and access to combat commands.
    """

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.max_hp = 100  # Set maximum HP to 100
        self.db.hp = self.db.max_hp  # Set current HP to maximum
        """
        Adds attributes for a character's current and maximum HP.
        We're just going to set this value at '100' by default.

        You may want to expand this to include various 'stats' that
        can be changed at creation and factor into combat calculations.
        """

    def at_before_move(self, destination):
        """
        Called just before starting to move this object to
        destination.

        Args:
            destination (Object): The object we are moving to

        Returns:
            shouldmove (bool): If we should move or not.

        Notes:
            If this method returns False/None, the move is cancelled
            before it is even started.

        """
        # Keep the character from moving if at 0 HP or in combat.
        if is_in_combat(self):
            self.msg("You can't exit a room while in combat!")
            return False  # Returning false keeps the character from moving.
        if self.db.HP <= 0:
            self.msg("You can't move, you've been defeated!")
            return False
        return True

"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBItemsTurnHandler(DefaultScript):
    """
    This is the script that handles the progression of combat through turns.
    On creation (when a fight is started) it adds all combat-ready characters
    to its roster and then sorts them into a turn order. There can only be one
    fight going on in a single room at a time, so the script is assigned to a
    room as its object.

    Fights persist until only one participant is left with any HP or all
    remaining participants choose to end the combat with the 'disengage' command.
    """

    def at_script_creation(self):
        """
        Called once, when the script is created.
        """
        self.key = "Combat Turn Handler"
        self.interval = 5  # Once every 5 seconds
        self.persistent = True
        self.db.fighters = []

        # Add all fighters in the room with at least 1 HP to the combat."
        for thing in self.obj.contents:
            if thing.db.hp:
                self.db.fighters.append(thing)

        # Initialize each fighter for combat
        for fighter in self.db.fighters:
            self.initialize_for_combat(fighter)

        # Add a reference to this script to the room
        self.obj.db.combat_turnhandler = self

        # Roll initiative and sort the list of fighters depending on who rolls highest to determine turn order.
        # The initiative roll is determined by the roll_init function and can be customized easily.
        ordered_by_roll = sorted(self.db.fighters, key=roll_init, reverse=True)
        self.db.fighters = ordered_by_roll

        # Announce the turn order.
        self.obj.msg_contents("Turn order is: %s " % ", ".join(obj.key for obj in self.db.fighters))
        
        # Start first fighter's turn.
        self.start_turn(self.db.fighters[0])

        # Set up the current turn and turn timeout delay.
        self.db.turn = 0
        self.db.timer = TURN_TIMEOUT  # Set timer to turn timeout specified in options

    def at_stop(self):
        """
        Called at script termination.
        """
        for fighter in self.db.fighters:
            combat_cleanup(fighter)  # Clean up the combat attributes for every fighter.
        self.obj.db.combat_turnhandler = None  # Remove reference to turn handler in location

    def at_repeat(self):
        """
        Called once every self.interval seconds.
        """
        currentchar = self.db.fighters[self.db.turn]  # Note the current character in the turn order.
        self.db.timer -= self.interval  # Count down the timer.

        if self.db.timer <= 0:
            # Force current character to disengage if timer runs out.
            self.obj.msg_contents("%s's turn timed out!" % currentchar)
            spend_action(currentchar, 'all', action_name="disengage")  # Spend all remaining actions.
            return
        elif self.db.timer <= 10 and not self.db.timeout_warning_given:  # 10 seconds left
            # Warn the current character if they're about to time out.
            currentchar.msg("WARNING: About to time out!")
            self.db.timeout_warning_given = True

    def initialize_for_combat(self, character):
        """
        Prepares a character for combat when starting or entering a fight.

        Args:
            character (obj): Character to initialize for combat.
        """
        combat_cleanup(character)  # Clean up leftover combat attributes beforehand, just in case.
        character.db.combat_actionsleft = 0  # Actions remaining - start of turn adds to this, turn ends when it reaches 0
        character.db.combat_turnhandler = self  # Add a reference to this turn handler script to the character
        character.db.combat_lastaction = "null"  # Track last action taken in combat

    def start_turn(self, character):
        """
        Readies a character for the start of their turn by replenishing their
        available actions and notifying them that their turn has come up.

        Args:
            character (obj): Character to be readied.

        Notes:
            Here, you only get one action per turn, but you might want to allow more than
            one per turn, or even grant a number of actions based on a character's
            attributes. You can even add multiple different kinds of actions, I.E. actions
            separated for movement, by adding "character.db.combat_movesleft = 3" or
            something similar.
        """
        character.db.combat_actionsleft = ACTIONS_PER_TURN  # Replenish actions
        # Prompt the character for their turn and give some information.
        character.msg("|wIt's your turn! You have %i HP remaining.|n" % character.db.hp)

    def next_turn(self):
        """
        Advances to the next character in the turn order.
        """

        # Check to see if every character disengaged as their last action. If so, end combat.
        disengage_check = True
        for fighter in self.db.fighters:
            if fighter.db.combat_lastaction != "disengage":  # If a character has done anything but disengage
                disengage_check = False
        if disengage_check:  # All characters have disengaged
            self.obj.msg_contents("All fighters have disengaged! Combat is over!")
            self.stop()  # Stop this script and end combat.
            return

        # Check to see if only one character is left standing. If so, end combat.
        defeated_characters = 0
        for fighter in self.db.fighters:
            if fighter.db.HP == 0:
                defeated_characters += 1  # Add 1 for every fighter with 0 HP left (defeated)
        if defeated_characters == (len(self.db.fighters) - 1):  # If only one character isn't defeated
            for fighter in self.db.fighters:
                if fighter.db.HP != 0:
                    LastStanding = fighter  # Pick the one fighter left with HP remaining
            self.obj.msg_contents("Only %s remains! Combat is over!" % LastStanding)
            self.stop()  # Stop this script and end combat.
            return

        # Cycle to the next turn.
        currentchar = self.db.fighters[self.db.turn]
        self.db.turn += 1  # Go to the next in the turn order.
        if self.db.turn > len(self.db.fighters) - 1:
            self.db.turn = 0  # Go back to the first in the turn order once you reach the end.
        newchar = self.db.fighters[self.db.turn]  # Note the new character
        self.db.timer = TURN_TIMEOUT + self.time_until_next_repeat()  # Reset the timer.
        self.db.timeout_warning_given = False  # Reset the timeout warning.
        self.obj.msg_contents("%s's turn ends - %s's turn begins!" % (currentchar, newchar))
        self.start_turn(newchar)  # Start the new character's turn.

    def turn_end_check(self, character):
        """
        Tests to see if a character's turn is over, and cycles to the next turn if it is.

        Args:
            character (obj): Character to test for end of turn
        """
        if not character.db.combat_actionsleft:  # Character has no actions remaining
            self.next_turn()
            return

    def join_fight(self, character):
        """
        Adds a new character to a fight already in progress.

        Args:
            character (obj): Character to be added to the fight.
        """
        # Inserts the fighter to the turn order, right behind whoever's turn it currently is.
        self.db.fighters.insert(self.db.turn, character)
        # Tick the turn counter forward one to compensate.
        self.db.turn += 1
        # Initialize the character like you do at the start.
        self.initialize_for_combat(character)

        
"""
----------------------------------------------------------------------------
COMMANDS START HERE
----------------------------------------------------------------------------
"""


class CmdFight(Command):
    """
    Starts a fight with everyone in the same room as you.

    Usage:
      fight

    When you start a fight, everyone in the room who is able to
    fight is added to combat, and a turn order is randomly rolled.
    When it's your turn, you can attack other characters.
    """
    key = "fight"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        here = self.caller.location
        fighters = []

        if not self.caller.db.hp:  # If you don't have any hp
            self.caller.msg("You can't start a fight if you've been defeated!")
            return
        if is_in_combat(self.caller):  # Already in a fight
            self.caller.msg("You're already in a fight!")
            return
        for thing in here.contents:  # Test everything in the room to add it to the fight.
            if thing.db.HP:  # If the object has HP...
                fighters.append(thing)  # ...then add it to the fight.
        if len(fighters) <= 1:  # If you're the only able fighter in the room
            self.caller.msg("There's nobody here to fight!")
            return
        if here.db.combat_turnhandler:  # If there's already a fight going on...
            here.msg_contents("%s joins the fight!" % self.caller)
            here.db.combat_turnhandler.join_fight(self.caller)  # Join the fight!
            return
        here.msg_contents("%s starts a fight!" % self.caller)
        # Add a turn handler script to the room, which starts combat.
        here.scripts.add("contrib.turnbattle.tb_items.TBItemsTurnHandler")
        # Remember you'll have to change the path to the script if you copy this code to your own modules!


class CmdAttack(Command):
    """
    Attacks another character.

    Usage:
      attack <target>

    When in a fight, you may attack another character. The attack has
    a chance to hit, and if successful, will deal damage.
    """

    key = "attack"
    help_category = "combat"

    def func(self):
        "This performs the actual command."
        "Set the attacker to the caller and the defender to the target."

        if not is_in_combat(self.caller):  # If not in combat, can't attack.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn, can't attack.
            self.caller.msg("You can only do that on your turn.")
            return

        if not self.caller.db.hp:  # Can't attack if you have no HP.
            self.caller.msg("You can't attack, you've been defeated.")
            return

        attacker = self.caller
        defender = self.caller.search(self.args)

        if not defender:  # No valid target given.
            return

        if not defender.db.hp:  # Target object has no HP left or to begin with
            self.caller.msg("You can't fight that!")
            return

        if attacker == defender:  # Target and attacker are the same
            self.caller.msg("You can't attack yourself!")
            return

        "If everything checks out, call the attack resolving function."
        resolve_attack(attacker, defender)
        spend_action(self.caller, 1, action_name="attack")  # Use up one action.


class CmdPass(Command):
    """
    Passes on your turn.

    Usage:
      pass

    When in a fight, you can use this command to end your turn early, even
    if there are still any actions you can take.
    """

    key = "pass"
    aliases = ["wait", "hold"]
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        if not is_in_combat(self.caller):  # Can only pass a turn in combat.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # Can only pass if it's your turn.
            self.caller.msg("You can only do that on your turn.")
            return

        self.caller.location.msg_contents("%s takes no further action, passing the turn." % self.caller)
        spend_action(self.caller, 'all', action_name="pass")  # Spend all remaining actions.


class CmdDisengage(Command):
    """
    Passes your turn and attempts to end combat.

    Usage:
      disengage

    Ends your turn early and signals that you're trying to end
    the fight. If all participants in a fight disengage, the
    fight ends.
    """

    key = "disengage"
    aliases = ["spare"]
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        if not is_in_combat(self.caller):  # If you're not in combat
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn
            self.caller.msg("You can only do that on your turn.")
            return

        self.caller.location.msg_contents("%s disengages, ready to stop fighting." % self.caller)
        spend_action(self.caller, 'all', action_name="disengage")  # Spend all remaining actions.
        """
        The action_name kwarg sets the character's last action to "disengage", which is checked by
        the turn handler script to see if all fighters have disengaged.
        """


class CmdRest(Command):
    """
    Recovers damage.

    Usage:
      rest

    Resting recovers your HP to its maximum, but you can only
    rest if you're not in a fight.
    """

    key = "rest"
    help_category = "combat"

    def func(self):
        "This performs the actual command."

        if is_in_combat(self.caller):  # If you're in combat
            self.caller.msg("You can't rest while you're in combat.")
            return

        self.caller.db.hp = self.caller.db.max_hp  # Set current HP to maximum
        self.caller.location.msg_contents("%s rests to recover HP." % self.caller)
        """
        You'll probably want to replace this with your own system for recovering HP.
        """


class CmdCombatHelp(CmdHelp):
    """
    View help or a list of topics

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game.
    """
    # Just like the default help command, but will give quick
    # tips on combat when used in a fight with no arguments.

    def func(self):
        if is_in_combat(self.caller) and not self.args:  # In combat and entered 'help' alone
            self.caller.msg("Available combat commands:|/" +
                            "|wAttack:|n Attack a target, attempting to deal damage.|/" +
                            "|wPass:|n Pass your turn without further action.|/" +
                            "|wDisengage:|n End your turn and attempt to end combat.|/")
        else:
            super(CmdCombatHelp, self).func()  # Call the default help command


class CmdUse(MuxCommand):
    """
    Use an item.

    Usage:
      use <item> [= target]

    Items: you just GOTTA use them.
    """

    key = "use"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        item = self.caller.search(self.lhs, candidates=self.caller.contents)
        if not item:
            return
        
        target = None
        if self.rhs:
            target = self.caller.search(self.rhs)
            if not target:
                return
                
        if is_in_combat(self.caller):
            if not is_turn(self.caller):
                self.caller.msg("You can only use items on your turn.")
                return
            
        if not item.db.item_func: # Object has no item_func, not usable
            self.caller.msg("'%s' is not a usable item." % item.key.capitalize())
            return
            
        if item.attributes.has("item_uses"): # Item has limited uses
            if item.db.item_uses <= 0: # Limited uses are spent
                self.caller.msg("'%s' has no uses remaining." % item.key.capitalize())
                return
        
        kwargs = {}
        if item.db.item_kwargs: 
            kwargs = item.db.item_kwargs # Set kwargs to pass to item_func
            
        # Match item_func string to function
        try:
            item_func = ITEMFUNCS[item.db.item_func]
        except KeyError:
            self.caller.msg("ERROR: %s not defined in ITEMFUNCS" % item.db.item_func)
            return
        
        # Call the item function - abort if it returns False, indicating an error.
        # Regardless of what the function returns (if anything), it's still executed.
        if item_func(item, self.caller, target, **kwargs) == False:
            return
            
        # If we haven't returned yet, we assume the item was used successfully.
            
        # Spend one use if item has limited uses
        spend_item_use(item)
            
        # Spend an action if in combat
        if is_in_combat(self.caller):
            spend_action(self.caller, 1, action_name="item")


class BattleCmdSet(default_cmds.CharacterCmdSet):
    """
    This command set includes all the commmands used in the battle system.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        self.add(CmdFight())
        self.add(CmdAttack())
        self.add(CmdRest())
        self.add(CmdPass())
        self.add(CmdDisengage())
        self.add(CmdCombatHelp())
        self.add(CmdUse())
        
"""
ITEM FUNCTIONS START HERE
"""

def itemfunc_heal(item, user, target, **kwargs):
    """
    Item function that heals HP.
    """
    if not target: 
        target = user # Target user if none specified
    
    if not target.attributes.has("max_hp"): # Has no HP to speak of
        user.msg("You can't use %s on that." % item)
        return False
        
    if target.db.hp >= target.db.max_hp:
        user.msg("%s is already at full health." % target)
        return False
    
    min_healing = 20
    max_healing = 40
    
    # Retrieve healing range from kwargs, if present
    if "healing_range" in kwargs:
        min_healing = kwargs["healing_range"][0]
        max_healing = kwargs["healing_range"][1]

    to_heal = randint(min_healing, max_healing) # Restore 20 to 40 hp
    if target.db.hp + to_heal > target.db.max_hp:
        to_heal = target.db.max_hp - target.db.hp # Cap healing to max HP
    target.db.hp += to_heal
    
    user.location.msg_contents("%s uses %s! %s regains %i HP!" % (user, item, target, to_heal))
    
def itemfunc_attack(item, user, target, **kwargs):
    """
    Item function that attacks a target.
    """
    if not is_in_combat(user):
        user.msg("You can only use that in combat.")
        return False
    
    if not target: 
        user.msg("You have to specify a target to use %s! (use <item> = <target>)" % item)
        return False
        
    if target == user:
        user.msg("You can't attack yourself!")
        return False
    
    if not target.db.hp: # Has no HP
        user.msg("You can't use %s on that." % item)
        return False
    
    min_damage = 20
    max_damage = 40
    accuracy = 0
    
    # Retrieve values from kwargs, if present
    if "damage_range" in kwargs:
        min_damage = kwargs["damage_range"][0]
        max_damage = kwargs["damage_range"][1]
    if "accuracy" in kwargs:
        accuracy = kwargs["accuracy"]
        
    # Roll attack and damage
    attack_value = randint(1, 100) + accuracy
    damage_value = randint(min_damage, max_damage)
    
    user.location.msg_contents("%s attacks %s with %s!" % (user, target, item))
    resolve_attack(user, target, attack_value=attack_value, damage_value=damage_value)

# Match strings to item functions here. We can't store callables on
# prototypes, so we store a string instead, matching that string to
# a callable in this dictionary.
ITEMFUNCS = {
    "heal":itemfunc_heal,
    "attack":itemfunc_attack
}

"""
ITEM PROTOTYPES START HERE
"""

MEDKIT = {
 "key" : "a medical kit",
 "aliases" : ["medkit"],
 "desc" : "A standard medical kit. It can be used a few times to heal wounds.",
 "item_func" : "heal",
 "item_uses" : 3,
 "item_consumable" : True,
 "item_kwargs" : {"healing_range":(15, 25)}
}

GLASS_BOTTLE = {
 "key" : "a glass bottle",
 "desc" : "An empty glass bottle."
}

HEALTH_POTION = {
 "key" : "a health potion",
 "desc" : "A glass bottle full of a mystical potion that heals wounds when used.",
 "item_func" : "heal",
 "item_uses" : 1,
 "item_consumable" : "GLASS_BOTTLE",
 "item_kwargs" : {"healing_range":(35, 50)}
}

BOMB = {
 "key" : "a rotund bomb",
 "desc" : "A large black sphere with a fuse at the end. Can be used on enemies in combat.",
 "item_func" : "attack",
 "item_uses" : 1,
 "item_consumable" : True,
 "item_kwargs" : {"damage_range":(25, 40), "accuracy":25}
}