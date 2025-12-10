#!/usr/bin/env python3
"""
Sabacc con i Tarocchi - Core Game Engine
A card game blending poker betting, rummy-style draws, and blackjack scoring
"""

import random
import os
from typing import List, Tuple, Optional

# Type aliases for clarity
Card = Tuple[str, str]  # (rank, suit)
Hand = List[Card]


def load_player_names() -> List[str]:
    """
    Load Star Wars character names from player_names.md file.

    Returns:
        List of character names. Falls back to generic names if file not found.
    """
    names = []
    names_file = os.path.join(os.path.dirname(__file__), 'player_names.md')

    try:
        with open(names_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and the header
                if line and not line.startswith('#'):
                    names.append(line)
    except FileNotFoundError:
        # Fallback to generic names if file doesn't exist
        names = [f"AI_{i}" for i in range(1, 21)]

    return names


def get_random_opponent_names(count: int) -> List[str]:
    """
    Get a random selection of unique opponent names.

    Args:
        count: Number of names to select

    Returns:
        List of randomly selected unique names
    """
    all_names = load_player_names()

    if count > len(all_names):
        # If we need more names than available, add generic ones
        all_names.extend([f"AI_{i}" for i in range(len(all_names) + 1, count + 1)])

    return random.sample(all_names, count)


class Deck:
    """Manages the 78-card Tarot deck"""

    def __init__(self):
        self.cards: List[Card] = []
        self._generate_deck()

    def _generate_deck(self):
        """Generate the complete 78-card Tarot deck"""
        self.cards = []

        # Trionfi (Trump cards): 0-21
        for rank in range(22):
            self.cards.append((str(rank), 'T'))

        # Four suits: Wands, Cups, Swords, Disks
        for suit in ['W', 'C', 'S', 'D']:
            # Numbered cards: 1-10
            for rank in range(1, 11):
                self.cards.append((str(rank), suit))

            # Court cards: Page, Knight, Queen, King
            for rank in ['P', 'N', 'Q', 'K']:
                self.cards.append((rank, suit))

    def shuffle(self):
        """Shuffle the deck"""
        random.shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        """Draw a card from the top of the deck"""
        return self.cards.pop(0) if self.cards else None


class Player:
    """Represents a player in the game"""

    def __init__(self, name: str, credits: int, is_human: bool = False):
        self.name = name
        self.credits = credits
        self.is_human = is_human
        self.hand: Hand = []
        self.current_bet = 0
        self.has_folded = False
        self.has_drawn = False
        self.has_acted = False

    def reset_for_new_hand(self):
        """Reset player state for a new hand"""
        self.hand = []
        self.current_bet = 0
        self.has_folded = False
        self.has_drawn = False
        self.has_acted = False
        self.is_hermit = False


class GameState:
    """Manages the overall game state"""

    def __init__(self, player_names: List[str], starting_credits: int = 500, min_bet: int = 2):
        # Players
        self.players: List[Player] = []
        for i, name in enumerate(player_names):
            is_human = (i == 0)  # First player is human
            self.players.append(Player(name, starting_credits, is_human))

        # Piles
        self.draw_pile = Deck()
        self.discard_pile: List[Card] = []
        self.community_cards: List[Card] = []
        self.removed_pile: List[Card] = []  # For Trionfi effects

        # Game state
        self.pot = 0
        self.current_bet = 0
        self.min_bet = min_bet
        self.dealer_index = 0
        self.hand_number = 0
        self.hands_face_up = False
        self.judgment_played = False
        self.tiebreaker_info = None

    def start_new_hand(self):
        """Initialize a new hand"""
        self.hand_number += 1
        self.pot = 0
        self.current_bet = 0
        self.hands_face_up = False
        self.judgment_played = False

        # Reset all players
        for player in self.players:
            player.reset_for_new_hand()

        # Reset piles - everything goes back into the deck for a fresh shuffle
        self.draw_pile = Deck()
        self.draw_pile.shuffle()
        self.discard_pile = []
        self.community_cards = []
        self.removed_pile = []

    def cards_remaining_in_draw_pile(self) -> int:
        """Return number of cards left in draw pile"""
        return len(self.draw_pile.cards)

    def cards_in_discard_pile(self) -> int:
        """Return number of cards in discard pile"""
        return len(self.discard_pile)

    def cards_in_removed_pile(self) -> int:
        """Return number of cards in removed pile (for Trionfi effects)"""
        return len(self.removed_pile)

    def total_cards_accounted_for(self) -> int:
        """
        Count all cards in the game to verify we haven't lost any.
        Should equal 78.
        """
        total = 0
        total += self.cards_remaining_in_draw_pile()
        total += self.cards_in_discard_pile()
        total += len(self.community_cards)

        # Count cards in all player hands
        for player in self.players:
            total += len(player.hand)

        # Removed cards
        total += self.cards_in_removed_pile()

        return total

    def reshuffle_discard_into_draw(self):
        """
        When draw pile is low, shuffle discard pile back into draw pile.
        """
        print(f"Draw pile low ({self.cards_remaining_in_draw_pile()} cards). Reshuffling discard pile...")
        self.draw_pile.cards.extend(self.discard_pile)
        self.discard_pile = []
        self.draw_pile.shuffle()
        print(f"Draw pile now has {self.cards_remaining_in_draw_pile()} cards.")

    def ensure_cards_available(self, num_needed: int = 1):
        """
        Ensure the draw pile has enough cards, reshuffling if necessary.

        Args:
            num_needed: Number of cards needed for the next operation
        """
        if self.cards_remaining_in_draw_pile() < num_needed:
            if self.cards_in_discard_pile() > 0:
                self.reshuffle_discard_into_draw()
            else:
                raise RuntimeError("Not enough cards available in draw or discard pile!")

    def deal_initial_cards(self):
        """
        Deal the initial hand: 2 cards to each player, 3 community cards, burn 1
        """
        # Make sure we have enough cards
        cards_needed = (len(self.players) * 2) + 3 + 1
        self.ensure_cards_available(cards_needed)

        # Deal 2 cards to each player
        for player in self.players:
            player.hand.append(self.draw_pile.draw())
            player.hand.append(self.draw_pile.draw())

        # Deal 3 community cards (the flop)
        for _ in range(3):
            card = self.draw_pile.draw()
            self.community_cards.append(card)

        # Burn one card
        burned = self.draw_pile.draw()
        self.discard_pile.append(burned)

    def deal_turn(self):
        """Add one card to community pool (the turn), burn one"""
        self.ensure_cards_available(2)

        # Burn one
        burned = self.draw_pile.draw()
        self.discard_pile.append(burned)

        # Turn one
        card = self.draw_pile.draw()
        self.community_cards.append(card)

    def deal_river(self):
        """Add one card to community pool (the river), burn one"""
        self.ensure_cards_available(2)

        # Burn one
        burned = self.draw_pile.draw()
        self.discard_pile.append(burned)

        # Turn one
        card = self.draw_pile.draw()
        self.community_cards.append(card)

    def reset_draw_flags(self):
        """
        Reset the has_drawn flag for all players at the start of a new betting round.
        """
        for player in self.players:
            player.has_drawn = False

    def reset_for_betting_round(self):
        """
        Reset player states at the start of a new betting round.
        Called before turn and river betting rounds (not the initial round).
        """
        for player in self.players:
            player.has_drawn = False
            player.has_acted = False
            player.current_bet = 0  # Reset bets for new round

        self.current_bet = 0  # Reset current bet for new round

    def draw_from_draw_pile(self, player: Player) -> Card:
        """
        Player draws the top card from the draw pile.

        Returns:
            The card drawn
        """
        self.ensure_cards_available(1)
        card = self.draw_pile.draw()
        player.hand.append(card)
        player.has_drawn = True
        return card

    def draw_from_discard_pile(self, player: Player, card_index: int) -> List[Card]:
        """
        Player draws a card from the discard pile and all cards above it.
        Index 0 is the bottom (oldest) card, so taking from there means taking everything.

        Args:
            card_index: Index of the card to take (0 = bottom/oldest)

        Returns:
            List of cards drawn
        """
        if not self.discard_pile:
            raise ValueError("Discard pile is empty!")

        if card_index < 0 or card_index >= len(self.discard_pile):
            raise ValueError(f"Invalid card index: {card_index}")

        # Take the card and everything above it (higher indices)
        cards_taken = self.discard_pile[card_index:]
        self.discard_pile = self.discard_pile[:card_index]

        player.hand.extend(cards_taken)
        player.has_drawn = True
        return cards_taken

    def swap_with_community(self, player: Player, hand_card_index: int, community_card_index: int) -> Tuple[Card, Card]:
        """
        Player swaps a card from their hand with a community card.
        The card from the player's hand becomes the new community card.

        Args:
            hand_card_index: Index of card in player's hand to swap out
            community_card_index: Index of community card to take

        Returns:
            (card_given, card_taken) tuple
        """
        if hand_card_index < 0 or hand_card_index >= len(player.hand):
            raise ValueError(f"Invalid hand card index: {hand_card_index}")

        if community_card_index < 0 or community_card_index >= len(self.community_cards):
            raise ValueError(f"Invalid community card index: {community_card_index}")

        # Swap the cards
        card_from_hand = player.hand.pop(hand_card_index)
        card_from_community = self.community_cards[community_card_index]
        self.community_cards[community_card_index] = card_from_hand
        player.hand.append(card_from_community)

        player.has_drawn = True
        return (card_from_hand, card_from_community)

    def discard_card(self, player: Player, card_index: int) -> Card:
        """
        Player discards a card from their hand face-up to the discard pile.

        Args:
            card_index: Index of card in player's hand to discard

        Returns:
            The discarded card
        """
        if card_index < 0 or card_index >= len(player.hand):
            raise ValueError(f"Invalid card index: {card_index}")

        card = player.hand.pop(card_index)
        self.discard_pile.append(card)
        return card

    def collect_blinds(self):
        """
        Collect small blind and big blind at the start of a hand.
        Small blind is from the player left of dealer.
        Big blind is from the player two left of dealer.
        """
        num_players = len(self.players)

        # Small blind (player left of dealer)
        sb_index = (self.dealer_index + 1) % num_players
        sb_player = self.players[sb_index]
        sb_amount = self.min_bet // 2

        # Collect small blind
        if sb_player.credits >= sb_amount:
            sb_player.credits -= sb_amount
            sb_player.current_bet = sb_amount
            self.pot += sb_amount
            print(f"{sb_player.name} posts small blind: {sb_amount}")
        else:
            # Player doesn't have enough, goes all-in
            sb_player.current_bet = sb_player.credits
            self.pot += sb_player.credits
            print(f"{sb_player.name} goes all-in for small blind: {sb_player.credits}")
            sb_player.credits = 0

        # Big blind (player two left of dealer)
        bb_index = (self.dealer_index + 2) % num_players
        bb_player = self.players[bb_index]
        bb_amount = self.min_bet

        # Collect big blind
        if bb_player.credits >= bb_amount:
            bb_player.credits -= bb_amount
            bb_player.current_bet = bb_amount
            self.pot += bb_amount
            self.current_bet = bb_amount
            print(f"{bb_player.name} posts big blind: {bb_amount}")
        else:
            # Player doesn't have enough, goes all-in
            bb_player.current_bet = bb_player.credits
            self.pot += bb_player.credits
            self.current_bet = bb_player.credits
            print(f"{bb_player.name} goes all-in for big blind: {bb_player.credits}")
            bb_player.credits = 0

    def player_fold(self, player: Player):
        """Player folds and is out of the hand"""
        player.has_folded = True
        player.has_acted = True
        print(f"{player.name} folds.")

    def player_call(self, player: Player) -> int:
        """
        Player calls the current bet.

        Returns:
            Amount added to pot
        """
        amount_to_call = self.current_bet - player.current_bet

        if amount_to_call <= 0:
            # Player is already at current bet (can check)
            print(f"{player.name} checks.")
            player.has_acted = True
            return 0

        # Check if player has enough credits
        if player.credits < amount_to_call:
            # Player is all-in
            amount_to_call = player.credits
            print(f"{player.name} goes all-in with {amount_to_call} credits!")
        else:
            print(f"{player.name} calls {amount_to_call}.")

        player.credits -= amount_to_call
        player.current_bet += amount_to_call
        self.pot += amount_to_call
        player.has_acted = True

        return amount_to_call

    def player_raise(self, player: Player, raise_amount: int) -> int:
        """
        Player raises the bet.

        Args:
            raise_amount: Additional amount to raise (on top of calling)

        Returns:
            Total amount added to pot
        """
        # First call the current bet
        amount_to_call = self.current_bet - player.current_bet

        # Then add the raise
        total_bet = amount_to_call + raise_amount

        # Check if player has enough credits
        if player.credits < total_bet:
            # Player can only go all-in
            actual_raise = player.credits - amount_to_call
            total_bet = player.credits
            print(f"{player.name} goes all-in! Raises {actual_raise} (total bet: {total_bet})")
        else:
            print(f"{player.name} raises {raise_amount} (total bet: {player.current_bet + total_bet})")

        player.credits -= total_bet
        player.current_bet += total_bet
        self.pot += total_bet

        # Update the current bet for other players
        self.current_bet = player.current_bet

        # When someone raises, all other active players need to act again
        for p in self.players:
            if p != player and not p.has_folded and p.credits > 0:
                p.has_acted = False

        player.has_acted = True

        return total_bet

    def is_betting_round_complete(self) -> bool:
        """
        Check if the betting round is complete.
        A round is complete when all active players have:
        - Acted at least once, AND
        - Either matched the current bet, folded, or gone all-in
        """
        active_players = [p for p in self.players if not p.has_folded]

        if len(active_players) <= 1:
            # Only one player left, round is over
            return True

        # Check if all active players have acted and matched the bet
        for player in active_players:
            # If player hasn't acted yet, round continues
            if not player.has_acted:
                return False

            # Skip players who are all-in (they can't act further)
            if player.credits == 0:
                continue

            # If any player hasn't matched the current bet, round continues
            if player.current_bet < self.current_bet:
                return False

        return True

    def get_active_players(self) -> List[Player]:
        """Return list of players who haven't folded"""
        return [p for p in self.players if not p.has_folded]

    def advance_dealer(self):
        """Move the dealer button to the next player"""
        self.dealer_index = (self.dealer_index + 1) % len(self.players)
        print(f"\nDealer button moves to {self.players[self.dealer_index].name}")

    def determine_winner(self) -> Optional[Player]:
        """
        Determine the winner at showdown.

        Returns:
            The winning player, or None if no one is eligible

        Sets self.tiebreaker_info with details about how winner was determined
        """
        # Reset tiebreaker info
        self.tiebreaker_info = None

        active_players = self.get_active_players()

        if len(active_players) == 0:
            return None

        if len(active_players) == 1:
            return active_players[0]

        # Calculate hand values for all active players
        player_scores = []
        for player in active_players:
            value, is_busted = calculate_hand_value(player.hand)
            if not is_busted:  # Only non-busted players can win
                distance_from_23 = abs(abs(value) - 23)
                player_scores.append((player, value, distance_from_23))

        if not player_scores:
            # Everyone busted - no winner
            return None

        # Sort by distance from 23 (closest first)
        player_scores.sort(key=lambda x: x[2])

        # Get all players tied for best score
        best_distance = player_scores[0][2]
        tied_players = [ps for ps in player_scores if ps[2] == best_distance]

        if len(tied_players) == 1:
            return tied_players[0][0]

        # Multiple players tied - record who was tied
        tied_names = [p[0].name for p in tied_players]
        tied_values = [p[1] for p in tied_players]

        # Tiebreaker: highest card value
        player_high_cards = []
        for player, value, distance in tied_players:
            high_card_value, high_card_suit = get_highest_card_in_hand(player.hand)
            player_high_cards.append((player, high_card_value, high_card_suit))

        # Sort by highest card value (descending)
        player_high_cards.sort(key=lambda x: x[1], reverse=True)

        highest_card_value = player_high_cards[0][1]
        still_tied = [phc for phc in player_high_cards if phc[1] == highest_card_value]

        if len(still_tied) == 1:
            winner = still_tied[0][0]
            winner_high_card_value = still_tied[0][1]
            self.tiebreaker_info = {
                'type': 'high_card',
                'tied_players': tied_names,
                'tied_values': tied_values,
                'winner_high_card': winner_high_card_value
            }
            return winner

        # Final tiebreaker: suit ranking (Wands > Cups > Swords > Disks)
        suit_ranking = {'W': 4, 'C': 3, 'S': 2, 'D': 1, 'T': 0}
        suit_names = {'W': 'Wands', 'C': 'Cups', 'S': 'Swords', 'D': 'Disks', 'T': 'Trionfi'}

        still_tied.sort(key=lambda x: suit_ranking.get(x[2], 0), reverse=True)

        winner = still_tied[0][0]
        winner_suit = still_tied[0][2]
        self.tiebreaker_info = {
            'type': 'suit',
            'tied_players': tied_names,
            'tied_values': tied_values,
            'winner_suit': suit_names.get(winner_suit, winner_suit)
        }

        return winner

    def award_pot(self, winner: Player):
        """
        Award the pot to the winning player.

        Args:
            winner: The player who won the hand
        """
        winner.credits += self.pot
        print(f"\n{winner.name} wins {self.pot} credits!")
        print(f"{winner.name} now has {winner.credits} credits.")
        self.pot = 0

    def execute_player_turn(self, player: Player, action: dict) -> bool:
        """
        Execute one player's turn in a betting round based on provided action.

        Args:
            player: The player taking the turn
            action: Dictionary containing the player's actions

        Returns:
            True if player is still in the hand, False if they folded
        """
        if player.has_folded:
            return False

        print(f"\n--- {player.name}'s Turn ---")

        # Step 0: Check for The Devil card - give it away if desired
        devil_card = ('15', 'T')
        if devil_card in player.hand:
            handle_devil_card(self, player)

        # Step 1: Betting action
        bet_action = action.get('bet_action', 'fold')

        if bet_action == 'fold':
            self.player_fold(player)
            return False

        elif bet_action == 'call':
            self.player_call(player)

        elif bet_action == 'raise':
            raise_amount = action.get('raise_amount', self.min_bet)
            self.player_raise(player, raise_amount)

            # Step 1.5: Play Trionfi special card if chosen
            if 'play_trionfi' in action:
                from sabacc_trionfi import get_trionfi_effect
                card = action['play_trionfi']
                trionfi = get_trionfi_effect(card)

                if trionfi and trionfi.effect:
                    # Check for Hanged Man interrupt
                    interrupted = check_for_hanged_man_interrupt(self, player, trionfi)

                    if not interrupted:
                        trionfi.apply_effect(self, player)

        # Step 2: Drawing (optional, only if player hasn't drawn yet)
        drew_card = False
        if not player.has_drawn:
            draw_action = action.get('draw_action')

            if draw_action == 'draw_pile':
                card = self.draw_from_draw_pile(player)
                print(f"Drew {card} from draw pile")
                drew_card = True

            elif draw_action == 'discard_pile':
                draw_index = action.get('draw_index', len(self.discard_pile) - 1)
                cards = self.draw_from_discard_pile(player, draw_index)
                print(f"Drew {len(cards)} card(s) from discard pile: {cards}")
                drew_card = True

            elif draw_action == 'community':
                hand_index = action.get('hand_card_index', 0)
                comm_index = action.get('community_card_index', 0)
                given, taken = self.swap_with_community(player, hand_index, comm_index)
                print(f"Swapped {given} for {taken}")
                drew_card = True

        # Step 2.5: For human players, show updated hand and ask about discarding
        if player.is_human and drew_card and action.get('ask_discard_after_draw'):
            from sabacc_game import calculate_hand_value
            value, busted = calculate_hand_value(player.hand)
            status = "BUSTED" if busted else "OK"
            print(f"\nYour hand is now: {player.hand}")
            print(f"Hand value: {value} [{status}]")

            discard_choice = input("\nDiscard a card? (y/n): ").strip().lower()
            if discard_choice == 'y':
                print("Which card to discard?")
                for i, card in enumerate(player.hand):
                    print(f"  {i}: {card}")
                while True:
                    try:
                        idx = int(input("Index: "))
                        if 0 <= idx < len(player.hand):
                            action['discard_index'] = idx
                            break
                        else:
                            print("Invalid index")
                    except ValueError:
                        print("Please enter a valid number")

        # Step 3: Discarding (optional)
        discard_index = action.get('discard_index')
        if discard_index is not None and 0 <= discard_index < len(player.hand):
            card = self.discard_card(player, discard_index)
            print(f"Discarded {card}")

        return True

    def run_betting_round(self, round_name: str = "Betting Round", get_ai_action_func=None):
        """
        Run a complete betting round, cycling through players until all have acted
        and matched the current bet (or folded/went all-in).

        Args:
            round_name: Name of the round for display purposes
            get_ai_action_func: Function to get AI player actions (imported from sabacc_ai)
        """
        print(f"\n{'=' * 50}")
        print(f"{round_name}")
        print(f"{'=' * 50}")

        # Determine starting player (left of dealer)
        num_players = len(self.players)
        start_index = (self.dealer_index + 1) % num_players

        # Keep cycling through players until betting round is complete
        current_index = start_index
        safety_counter = 0
        max_iterations = num_players * 10

        while not self.is_betting_round_complete() and safety_counter < max_iterations:
            player = self.players[current_index]

            # Skip players who have folded or are all-in
            if not player.has_folded and player.credits > 0:
                # Get action based on player type
                if player.is_human:
                    # This will be imported from sabacc_main
                    from sabacc_main import get_player_action_interactive
                    action = get_player_action_interactive(self, player)
                else:
                    # Use AI function passed in
                    if get_ai_action_func:
                        action = get_ai_action_func(self, player)
                    else:
                        # Fallback: just call
                        action = {'bet_action': 'call'}

                self.execute_player_turn(player, action)

            # Move to next player
            current_index = (current_index + 1) % num_players
            safety_counter += 1

        if safety_counter >= max_iterations:
            print("WARNING: Betting round took too many iterations!")

        print(f"\n{round_name} complete. Pot: {self.pot}")

    def _do_showdown(self):
        """
        Execute the showdown - determine and award winner.
        Called at the end of a hand or when The Last Judgment is played.
        """
        active_players = self.get_active_players()
        if len(active_players) <= 1:
            if len(active_players) == 1:
                print(f"\nAll other players folded. {active_players[0].name} wins by default!")
                self.award_pot(active_players[0])
        else:
            print(f"\n{'=' * 60}")
            print("SHOWDOWN")
            print(f"{'=' * 60}")

            # Show all active players' hands
            for player in active_players:
                value, is_busted = calculate_hand_value(player.hand)
                status = "BUSTED" if is_busted else "OK"
                print(f"{player.name}: {player.hand} = {value} [{status}]")

            # Determine winner
            winner = self.determine_winner()
            if winner:
                value, _ = calculate_hand_value(winner.hand)

                # Check if a tiebreaker was used
                if self.tiebreaker_info:
                    tb_info = self.tiebreaker_info
                    tied_str = " and ".join(tb_info['tied_players'])
                    values_str = ", ".join(str(v) for v in tb_info['tied_values'])

                    print(f"\n⚔️  TIE: {tied_str} are tied with values {values_str}")

                    if tb_info['type'] == 'high_card':
                        print(f"⚖️  TIEBREAKER: {winner.name} wins by high card (value {tb_info['winner_high_card']})!")
                    elif tb_info['type'] == 'suit':
                        print(f"⚖️  TIEBREAKER: {winner.name} wins by suit ({tb_info['winner_suit']})!")
                else:
                    print(f"\n🏆 {winner.name} wins with a hand value of {value}!")

                self.award_pot(winner)
            else:
                print("\nAll players busted! No winner. Pot carries over.")

    def play_hand(self, get_ai_action_func=None):
        """
        Play a complete hand from start to finish.

        Args:
            get_ai_action_func: Function to get AI player actions
        """
        print(f"\n{'#' * 60}")
        print(f"# HAND #{self.hand_number}")
        print(f"# Dealer: {self.players[self.dealer_index].name}")
        print(f"{'#' * 60}")

        # Step 1: Initialize hand
        self.start_new_hand()
        self.collect_blinds()

        # Step 2: Deal initial cards (flop)
        self.deal_initial_cards()
        print(f"\nFlop: {self.community_cards}")

        # Step 3: First betting round
        self.run_betting_round("First Betting Round (Flop)", get_ai_action_func)

        # Check if The Last Judgment was played
        if self.judgment_played:
            print("\nThe Last Judgment was played - skipping to showdown!")
            # Jump directly to showdown (Step 8)
            self._do_showdown()
            self.advance_dealer()
            return

        # Check if only one player remains
        active_players = self.get_active_players()
        if len(active_players) <= 1:
            if len(active_players) == 1:
                print(f"\nAll other players folded. {active_players[0].name} wins by default!")
                self.award_pot(active_players[0])
            self.advance_dealer()
            return

        # Step 4: Deal turn
        self.reset_for_betting_round()
        self.deal_turn()
        print(f"\nTurn: {self.community_cards}")

        # Step 5: Second betting round
        self.run_betting_round("Second Betting Round (Turn)", get_ai_action_func)

        # Check if The Last Judgment was played
        if self.judgment_played:
            print("\nThe Last Judgment was played - skipping to showdown!")
            self._do_showdown()
            self.advance_dealer()
            return

        # Check again if only one player remains
        active_players = self.get_active_players()
        if len(active_players) <= 1:
            if len(active_players) == 1:
                print(f"\nAll other players folded. {active_players[0].name} wins by default!")
                self.award_pot(active_players[0])
            self.advance_dealer()
            return

        # Step 6: Deal river
        self.reset_for_betting_round()
        self.deal_river()
        print(f"\nRiver: {self.community_cards}")

        # Step 7: Third betting round
        self.run_betting_round("Third Betting Round (River)", get_ai_action_func)

        # Step 8: Showdown
        self._do_showdown()

        # Move dealer button
        self.advance_dealer()

        # Show final chip counts
        print(f"\n{'=' * 60}")
        print("End of Hand - Chip Counts:")
        for player in self.players:
            print(f"  {player.name}: {player.credits} credits")
        print(f"{'=' * 60}")


def handle_devil_card(game: GameState, player: Player) -> None:
    """
    Handle The Devil card at the beginning of a player's turn.
    Player can choose to give it to another player.
    """
    devil_card = ('15', 'T')

    if player.is_human:
        print(f"\n😈 {player.name}, you have The Devil card (-15 points)!")
        print("Do you want to give it to another player? (y/n): ", end='')
        choice = input().strip().lower()

        if choice == 'y':
            # Get active players (not folded)
            eligible_targets = [p for p in game.players if p != player and not p.has_folded]

            if not eligible_targets:
                print("No eligible players to give The Devil to.")
                return

            print("\nChoose a player:")
            for i, target in enumerate(eligible_targets):
                print(f"  {i}: {target.name}")

            while True:
                try:
                    idx = int(input("Player index: ").strip())
                    if 0 <= idx < len(eligible_targets):
                        target = eligible_targets[idx]
                        break
                    else:
                        print("Invalid index")
                except ValueError:
                    print("Please enter a valid number")

            # Transfer the card
            player.hand.remove(devil_card)
            target.hand.append(devil_card)
            print(f"\n{player.name} gives The Devil to {target.name}!")
    else:
        # AI logic: decide whether to give away The Devil
        from sabacc_ai import should_give_away_devil, choose_devil_target

        if should_give_away_devil(game, player):
            eligible_targets = [p for p in game.players if p != player and not p.has_folded]

            if eligible_targets:
                target = choose_devil_target(game, player, eligible_targets)

                # Transfer the card
                player.hand.remove(devil_card)
                target.hand.append(devil_card)
                print(f"\n😈 {player.name} gives The Devil to {target.name}!")


def check_for_hanged_man_interrupt(game: GameState, acting_player: Player, trionfi) -> bool:
    """
    Check if anyone wants to play The Hanged Man to interrupt a special effect.

    Returns:
        True if the effect was interrupted, False otherwise
    """
    hanged_man_card = ('12', 'T')

    # Check all other players for The Hanged Man
    for player in game.players:
        if player == acting_player or player.has_folded:
            continue

        if hanged_man_card not in player.hand:
            continue

        # Player has The Hanged Man - ask if they want to use it
        if player.is_human:
            print(f"\n🙃 {player.name}, you have The Hanged Man!")
            print(f"Do you want to nullify {trionfi.name}? (y/n): ", end='')
            choice = input().strip().lower()

            if choice == 'y':
                print(f"\n{player.name} plays The Hanged Man - NOPE!")
                print(f"{trionfi.name}'s effect is nullified!")

                # Remove both cards
                player.hand.remove(hanged_man_card)
                game.removed_pile.append(hanged_man_card)

                trionfi_card = (str(trionfi.number), 'T')
                if trionfi_card in acting_player.hand:
                    acting_player.hand.remove(trionfi_card)
                    game.removed_pile.append(trionfi_card)

                return True
        else:
            # AI logic: interrupt if the effect would hurt them significantly
            from sabacc_ai import should_play_hanged_man

            if should_play_hanged_man(game, player, acting_player, trionfi):
                print(f"\n{player.name} plays The Hanged Man - NOPE!")
                print(f"{trionfi.name}'s effect is nullified!")

                # Remove both cards
                player.hand.remove(hanged_man_card)
                game.removed_pile.append(hanged_man_card)

                trionfi_card = (str(trionfi.number), 'T')
                if trionfi_card in acting_player.hand:
                    acting_player.hand.remove(trionfi_card)
                    game.removed_pile.append(trionfi_card)

                return True

    return False

def calculate_hand_value(hand: Hand) -> Tuple[int, bool]:
    """
    Calculate the value of a hand, optimizing ace values.

    The winning condition is based on absolute value closest to 23 without exceeding.
    So a hand worth -21 is as good as +21 (both are 2 away from 23).

    Returns:
        (value, is_busted) - the hand value and whether |value| exceeds 23
    """
    value = 0
    num_aces = 0
    has_lovers = False

    for rank, suit in hand:
        if suit == 'T':  # Trionfi
            # The Lovers: handle separately at end
            if rank == '6':
                has_lovers = True
            # Negative values: 2, 3, 8, 11, 13, 14, 15, 16, 17
            elif rank in ('2', '3', '8', '11', '13', '14', '15', '16', '17'):
                value -= int(rank)
            # All others worth 0
        else:  # Regular suits
            if rank == '1':  # Ace
                num_aces += 1
                value += 1  # Start with ace as 1
            elif rank == 'K':
                value += 14
            elif rank == 'Q':
                value += 13
            elif rank == 'N':
                value += 12
            elif rank == 'P':
                value += 11
            else:  # Numbered cards 2-10
                value += int(rank)

    # Optimize aces: for each ace, decide if making it 11 gets us closer to ±23
    for _ in range(num_aces):
        current_distance = abs(abs(value) - 23)
        new_value = value + 10
        new_distance = abs(abs(new_value) - 23)

        # Only add 10 if it gets us closer to ±23 AND doesn't bust us
        if new_distance < current_distance and abs(new_value) <= 23:
            value += 10

    # Handle The Lovers: choose +6 or -6 based on which is better
    if has_lovers:
        distance_plus = abs(abs(value + 6) - 23) if abs(value + 6) <= 23 else float('inf')
        distance_minus = abs(abs(value - 6) - 23) if abs(value - 6) <= 23 else float('inf')

        if distance_plus < distance_minus:
            value += 6
        else:
            value -= 6

    is_busted = abs(value) > 23
    return value, is_busted

def get_highest_card_in_hand(hand: Hand) -> Tuple[int, str]:
    """
    Get the value and suit of the highest-value card in a hand.
    Used for tiebreaking.

    Returns:
        (value, suit) tuple for the highest card
    """
    highest_value = -999  # Start very low to handle negative Trionfi
    highest_suit = ''

    for rank, suit in hand:
        card_value = 0

        if suit == 'T':  # Trionfi
            if rank in ('2', '3', '6', '8', '11', '13', '14', '15', '16', '17'):
                card_value = -int(rank)
            else:
                card_value = 0
        else:  # Regular suits
            if rank == '1':
                card_value = 11  # For comparison purposes, treat ace as 11
            elif rank == 'K':
                card_value = 14
            elif rank == 'Q':
                card_value = 13
            elif rank == 'N':
                card_value = 12
            elif rank == 'P':
                card_value = 11
            else:
                card_value = int(rank)

        if card_value > highest_value:
            highest_value = card_value
            highest_suit = suit

    return (highest_value, highest_suit)