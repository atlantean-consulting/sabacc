#!/usr/bin/env python3
"""
Sabacc con i Tarocchi - AI Player Logic
"""

import random
from sabacc_game import GameState, Player, calculate_hand_value


class OpponentModel:
    """
    Tracks statistics and tendencies for an opponent player.
    Used to adjust AI strategy based on observed behavior.
    """

    def __init__(self, player_name):
        self.player_name = player_name

        # Betting statistics
        self.hands_played = 0
        self.folds = 0
        self.calls = 0
        self.raises = 0

        # Showdown data
        self.showdowns = 0
        self.showdown_distances = []  # Track distance-to-23 values at showdown

        # Aggression metrics
        self.preflop_raises = 0
        self.postflop_raises = 0

    def record_action(self, action_type, is_preflop=False):
        """Record a betting action"""
        if action_type == 'fold':
            self.folds += 1
        elif action_type == 'call':
            self.calls += 1
        elif action_type == 'raise':
            self.raises += 1
            if is_preflop:
                self.preflop_raises += 1
            else:
                self.postflop_raises += 1

    def record_showdown(self, hand_distance):
        """Record hand strength shown at showdown"""
        self.showdowns += 1
        self.showdown_distances.append(hand_distance)

    def get_fold_frequency(self):
        """What % of time does this opponent fold?"""
        total_actions = self.folds + self.calls + self.raises
        if total_actions == 0:
            return 0.5  # Unknown, assume average
        return self.folds / total_actions

    def get_aggression_factor(self):
        """How aggressive is this opponent? (raises / calls)"""
        if self.calls == 0:
            return 1.0 if self.raises > 0 else 0.5
        return self.raises / (self.calls + self.raises)

    def get_average_showdown_distance(self):
        """What hand strength do they typically show at showdown?"""
        if not self.showdown_distances:
            return 10.0  # Unknown, assume medium strength
        return sum(self.showdown_distances) / len(self.showdown_distances)

    def is_tight_player(self):
        """Tight players fold often (>50%)"""
        return self.get_fold_frequency() > 0.5

    def is_loose_player(self):
        """Loose players fold rarely (<30%)"""
        return self.get_fold_frequency() < 0.3

    def is_aggressive_player(self):
        """Aggressive players raise often (aggression > 0.5)"""
        return self.get_aggression_factor() > 0.5

    def get_expected_hand_strength_multiplier(self):
        """
        Estimate how strong opponent's hand is likely to be based on their tendencies.
        Returns a multiplier for their estimated hand strength.

        Tight players: 0.8 (stronger than average)
        Loose players: 1.2 (weaker than average)
        Average: 1.0
        """
        fold_freq = self.get_fold_frequency()

        if fold_freq > 0.6:  # Very tight
            return 0.7
        elif fold_freq > 0.5:  # Tight
            return 0.85
        elif fold_freq < 0.25:  # Very loose
            return 1.3
        elif fold_freq < 0.35:  # Loose
            return 1.15
        else:  # Average
            return 1.0


# Global opponent models (keyed by player name)
OPPONENT_MODELS = {}


def get_opponent_model(player_name):
    """Get or create opponent model for a player"""
    if player_name not in OPPONENT_MODELS:
        OPPONENT_MODELS[player_name] = OpponentModel(player_name)
    return OPPONENT_MODELS[player_name]


def update_opponent_action(player_name, action_type, is_preflop=False):
    """Record an opponent's action for modeling"""
    model = get_opponent_model(player_name)
    model.record_action(action_type, is_preflop)


def update_opponent_showdown(player_name, hand):
    """Record an opponent's hand at showdown"""
    model = get_opponent_model(player_name)
    value, is_busted = calculate_hand_value(hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')
    model.record_showdown(distance)


def analyze_opponents(game: GameState, player: Player):
    """
    Analyze active opponents and adjust our win probability estimate.

    Returns:
        Adjustment factor for our win probability (0.8 to 1.2)
    """
    active_opponents = [p for p in game.players if p != player and not p.has_folded]

    if not active_opponents:
        return 1.0

    # Average the expected hand strength of all opponents
    total_multiplier = 0.0
    for opp in active_opponents:
        model = get_opponent_model(opp.name)
        total_multiplier += model.get_expected_hand_strength_multiplier()

    avg_multiplier = total_multiplier / len(active_opponents)

    # If opponents are tight (low multiplier), they likely have stronger hands
    # So our win probability should be adjusted down
    # If opponents are loose (high multiplier), adjust our win probability up

    # Invert the multiplier for our perspective
    # Tight opponent (0.8) -> we're less likely to win (0.9)
    # Loose opponent (1.2) -> we're more likely to win (1.1)
    our_adjustment = 1.0 + (1.0 - avg_multiplier) * 0.5

    return max(0.7, min(1.3, our_adjustment))


def get_simple_ai_action(game: GameState, player: Player) -> dict:
    """
    Generate an AI action with basic distance-to-23 evaluation.

    This AI uses distance from 23 to make decisions about:
    - Betting (based on hand strength)
    - Drawing (when hand needs improvement)
    - Discarding (removing cards that hurt hand value)

    Args:
        game: The current game state
        player: The AI player making the decision

    Returns:
        Action dictionary for execute_player_turn
    """
    value, is_busted = calculate_hand_value(player.hand)
    action = {}

    # Calculate how far we are from the target (23)
    if is_busted:
        distance_to_23 = float('inf')  # Busted is worst case
        hand_strength = 0.0
        estimated_win_probability = 0.0
    else:
        distance_to_23 = abs(abs(value) - 23)
        # Hand strength: 0.0 (distance=23) to 1.0 (distance=0)
        # This gives us a normalized measure of how good our hand is
        hand_strength = 1.0 - (distance_to_23 / 23.0)

        # Estimate win probability based on hand strength
        # Distance 0 (perfect) ~= 90% win rate (can still lose to ties/special effects)
        # Distance 5 ~= 60% win rate
        # Distance 10 ~= 35% win rate
        # Distance 15 ~= 15% win rate
        # Distance 20+ ~= 5% win rate
        base_win_probability = estimate_win_probability(distance_to_23)

        # Adjust win probability based on opponent tendencies
        opponent_adjustment = analyze_opponents(game, player)
        estimated_win_probability = base_win_probability * opponent_adjustment

        # Clamp to valid probability range
        estimated_win_probability = max(0.0, min(1.0, estimated_win_probability))

    amount_to_call = game.current_bet - player.current_bet

    # Calculate pot odds if there's a bet to call
    pot_odds_ratio = None
    if amount_to_call > 0 and player.credits > 0:
        # Pot odds = pot size / amount to call
        # Higher ratio = better odds (getting more for your investment)
        pot_odds_ratio = game.pot / amount_to_call

        # Break-even probability: what % of the time we need to win to break even
        # If pot odds are 3:1, we need to win 1/(1+3) = 25% of the time
        breakeven_probability = 1.0 / (1.0 + pot_odds_ratio)

    # === BETTING DECISION (using pot odds and opponent modeling) ===

    # Analyze opponents for bluffing opportunities
    active_opponents = [p for p in game.players if p != player and not p.has_folded]
    avg_opponent_fold_freq = 0.5  # Default
    if active_opponents:
        fold_freqs = [get_opponent_model(opp.name).get_fold_frequency() for opp in active_opponents]
        avg_opponent_fold_freq = sum(fold_freqs) / len(fold_freqs)

    # Bluff more against tight opponents, less against loose
    bluff_multiplier = avg_opponent_fold_freq / 0.5  # 1.0 = average, >1.0 = tight, <1.0 = loose

    # No bet to call - check or raise based on hand strength
    if amount_to_call == 0:
        # Strong hand (distance <= 3): mix of aggressive and deceptive plays
        if distance_to_23 <= 3:
            # Slow-play occasionally (10-20%) to trap opponents
            # More likely to slow-play against aggressive opponents
            slowplay_chance = 0.10
            if not get_opponent_model(active_opponents[0].name).is_aggressive_player() if active_opponents else False:
                slowplay_chance = 0.20  # Slow-play more vs aggressive players

            if random.random() < slowplay_chance:
                # Slow-play: check with strong hand
                action['bet_action'] = 'call'  # Check
            else:
                # Raise (varied sizing for deception)
                action['bet_action'] = 'raise'

                # Vary raise size: 60% normal, 30% small (trap), 10% large (value)
                size_roll = random.random()
                if size_roll < 0.30:  # Small raise to induce calls
                    raise_size = game.min_bet
                elif size_roll < 0.90:  # Standard raise
                    raise_size = max(game.min_bet, int(game.pot * 0.5))
                else:  # Large raise for value
                    raise_size = max(game.min_bet, int(game.pot * 0.75))

                action['raise_amount'] = min(raise_size, player.credits)

        # Good hand (distance 4-7): mix of value raises and checks
        elif distance_to_23 <= 7:
            # Raise 40% for value, check 60%
            if random.random() < 0.40:
                action['bet_action'] = 'raise'
                # Vary between min bet and 1/3 pot
                if random.random() < 0.7:
                    action['raise_amount'] = game.min_bet
                else:
                    action['raise_amount'] = max(game.min_bet, int(game.pot * 0.33))
            else:
                action['bet_action'] = 'call'  # Check

        # Medium hand (distance 8-12): semi-bluff or check
        elif distance_to_23 <= 12:
            # Semi-bluff: bluff with hands that could improve if we draw next round
            # More likely if we haven't drawn yet (could improve)
            semi_bluff_value = 1.5 if not player.has_drawn else 1.0

            bluff_chance = 0.15 * bluff_multiplier * semi_bluff_value

            # Only bluff if pot is worth it
            if random.random() < bluff_chance and game.pot > game.min_bet * 3:
                action['bet_action'] = 'raise'
                # Bluff with smaller sizing (looks like value bet)
                action['raise_amount'] = game.min_bet
            else:
                action['bet_action'] = 'call'  # Check

        # Weak hand (distance > 12): usually check, occasional pure bluff
        else:
            # Pure bluff: very rare, only against very tight opponents
            pure_bluff_chance = 0.05 * max(0, (bluff_multiplier - 1.0))  # Only vs tight

            if random.random() < pure_bluff_chance and game.pot > game.min_bet * 5:
                action['bet_action'] = 'raise'
                action['raise_amount'] = game.min_bet
            else:
                action['bet_action'] = 'call'  # Check

    # There's a bet to call - use pot odds to decide
    else:
        # If we're busted, fold unless pot odds are incredibly good
        if is_busted:
            if pot_odds_ratio and pot_odds_ratio > 10:  # Getting 10:1 or better
                action['bet_action'] = 'call'  # Might get lucky
            else:
                action['bet_action'] = 'fold'
                return action

        # Use pot odds: call if our win probability > breakeven probability
        # Add a small margin for error (require +5% edge)
        if pot_odds_ratio and estimated_win_probability > breakeven_probability + 0.05:
            # Pot odds justify a call
            action['bet_action'] = 'call'

            # Consider raising if hand is strong (deception mix)
            if distance_to_23 <= 3:
                # Strong hand: mix of raises and slow-play calls
                # 50% raise immediately, 50% slow-play call (might check-raise later)
                if random.random() < 0.50:
                    action['bet_action'] = 'raise'
                    # Vary raise size for deception
                    if random.random() < 0.4:
                        raise_size = max(game.min_bet, int(game.pot * 0.3))  # Small
                    else:
                        raise_size = max(game.min_bet, int(game.pot * 0.6))  # Large
                    action['raise_amount'] = min(raise_size, player.credits)
                # else: slow-play call (trap)

            # Good hand: occasionally raise for value
            elif distance_to_23 <= 7:
                if random.random() < 0.25:  # 25% raise
                    action['bet_action'] = 'raise'
                    raise_size = max(game.min_bet, int(game.pot * 0.4))
                    action['raise_amount'] = min(raise_size, player.credits)

        # Marginal situation: call if cheap, fold if expensive
        elif pot_odds_ratio and estimated_win_probability > breakeven_probability - 0.10:
            # Close to breakeven - call if it's cheap relative to our stack
            if amount_to_call <= player.credits // 10:  # Less than 10% of stack
                action['bet_action'] = 'call'
            else:
                action['bet_action'] = 'fold'
                return action

        # Pot odds don't justify a call
        else:
            # Normally fold, but occasionally make a "hero call" or "bad call"
            # This adds unpredictability and prevents being exploited
            # 5% of the time, make a marginal call even with bad odds

            hero_call_chance = 0.05

            # More likely to hero call vs aggressive opponents (they might be bluffing)
            if active_opponents:
                avg_aggression = sum(get_opponent_model(p.name).get_aggression_factor()
                                   for p in active_opponents) / len(active_opponents)
                if avg_aggression > 0.6:  # Very aggressive opponents
                    hero_call_chance = 0.12

            # Make hero call if:
            # 1. Random chance hits
            # 2. Bet is small relative to stack (< 15%)
            # 3. We're not completely busted
            if (random.random() < hero_call_chance and
                amount_to_call < player.credits * 0.15 and
                distance_to_23 < 18):
                action['bet_action'] = 'call'  # Hero call
            else:
                action['bet_action'] = 'fold'
                return action

    # === DRAWING DECISION ===
    # Draw if we're far from 23 and haven't drawn yet
    if not player.has_drawn:
        # Evaluate all three drawing options and pick the best

        # Option 1: Community card swap (all cards are visible)
        best_community_swap = evaluate_community_swaps(player.hand, game.community_cards)

        # Option 2: Discard pile draw (all cards are visible)
        best_discard_draw = evaluate_discard_pile_draws(player.hand, game.discard_pile)

        # Option 3: Draw pile (unknown card)
        # We'll consider this based on how far we are from target

        # Compare options and pick the best
        best_action = None
        best_improvement = 0

        # Check community swap
        if best_community_swap is not None:
            hand_idx, comm_idx, expected_distance = best_community_swap
            improvement = distance_to_23 - expected_distance
            if improvement > best_improvement:
                best_improvement = improvement
                best_action = ('community', hand_idx, comm_idx, expected_distance)

        # Check discard pile
        if best_discard_draw is not None:
            draw_idx, expected_distance = best_discard_draw
            improvement = distance_to_23 - expected_distance
            if improvement > best_improvement:
                best_improvement = improvement
                best_action = ('discard_pile', draw_idx, expected_distance)

        # Decide whether to take the best option or draw from draw pile
        if best_action is not None:
            action_type = best_action[0]

            # Take the visible card option if it significantly improves hand (>= 3 distance)
            # Or if we're desperate (distance > 15) and it helps at all
            if best_improvement >= 3 or (distance_to_23 > 15 and best_improvement > 0):
                if action_type == 'community':
                    _, hand_idx, comm_idx, _ = best_action
                    action['draw_action'] = 'community'
                    action['hand_card_index'] = hand_idx
                    action['community_card_index'] = comm_idx
                elif action_type == 'discard_pile':
                    _, draw_idx, _ = best_action
                    action['draw_action'] = 'discard_pile'
                    action['draw_index'] = draw_idx
            # Otherwise, consider draw pile as fallback
            elif distance_to_23 > 10:
                action['draw_action'] = 'draw_pile'
            elif distance_to_23 > 5 and random.random() < 0.6:
                action['draw_action'] = 'draw_pile'
            elif distance_to_23 > 2 and random.random() < 0.3:
                action['draw_action'] = 'draw_pile'
        else:
            # No good visible options, use draw pile if needed
            if distance_to_23 > 10:
                action['draw_action'] = 'draw_pile'
            elif distance_to_23 > 5 and random.random() < 0.6:
                action['draw_action'] = 'draw_pile'
            elif distance_to_23 > 2 and random.random() < 0.3:
                action['draw_action'] = 'draw_pile'
        # If we're very close (distance <= 2), don't draw

    # === DISCARDING DECISION ===
    # Only discard if we have more than 2 cards
    if len(player.hand) > 2:
        # Try to find the worst card to discard
        worst_card_index = find_worst_card_to_discard(player.hand)
        if worst_card_index is not None:
            # Discard more aggressively when hand is weak
            discard_chance = 0.7 if distance_to_23 > 10 else 0.4
            if random.random() < discard_chance:
                action['discard_index'] = worst_card_index

    return action


def should_play_wheel_of_fortune(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play Wheel of Fortune (Trionfo X) to draw 4 cards.

    Play it when:
    - Hand is weak and needs improvement
    - Similar to Magician but more immediate benefit

    Returns:
        True if AI should play Wheel of Fortune
    """
    from sabacc_game import calculate_hand_value

    value, is_busted = calculate_hand_value(player.hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')

    # Play if hand is weak (distance > 8) or busted
    if distance > 8 or is_busted:
        return True

    return False


def choose_wheel_of_fortune_cards(current_hand, drawn_cards):
    """
    Decide which of the 4 drawn cards to keep from Wheel of Fortune.

    Strategy:
    - Evaluate each card's contribution to hand value
    - Keep cards that improve distance to 23
    - Discard cards that hurt or don't help

    Args:
        current_hand: Player's hand before drawing
        drawn_cards: The 4 cards drawn

    Returns:
        List of cards to keep
    """
    from sabacc_game import calculate_hand_value
    from itertools import combinations

    # Current hand value
    current_value, current_busted = calculate_hand_value(current_hand)
    current_distance = abs(abs(current_value) - 23) if not current_busted else float('inf')

    best_kept_cards = []
    best_distance = current_distance

    # Try all possible combinations of keeping 0-4 cards
    for num_to_keep in range(len(drawn_cards) + 1):
        for cards_to_keep in combinations(drawn_cards, num_to_keep):
            test_hand = current_hand + list(cards_to_keep)
            test_value, test_busted = calculate_hand_value(test_hand)
            test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

            # Better than current best?
            if test_distance < best_distance:
                best_distance = test_distance
                best_kept_cards = list(cards_to_keep)

    return best_kept_cards


def should_play_hermit(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play The Hermit (Trionfo IX) to withdraw from betting.

    Play it when:
    - AI has a good hand but low credits (protect position)
    - Facing aggressive opponents (avoid pressure)
    - Want to lock in current hand without risking more

    Returns:
        True if AI should play The Hermit
    """
    from sabacc_game import calculate_hand_value

    # Get active opponents
    active_opponents = [p for p in game.players
                       if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not active_opponents:
        return False

    # Check AI's hand strength
    value, is_busted = calculate_hand_value(player.hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')

    # Don't play if hand is terrible
    if distance > 12 or is_busted:
        return False

    # Strategy 1: Low on credits with decent hand
    # Protect position without risking more chips
    if player.credits < game.min_bet * 5 and distance <= 8:
        return True

    # Strategy 2: Good hand facing multiple aggressive opponents
    # Avoid pressure and special effects
    if distance <= 5:
        aggressive_count = sum(1 for opp in active_opponents
                             if get_opponent_model(opp.name).is_aggressive_player())
        if aggressive_count >= 2:
            return True

    # Strategy 3: Strong hand with large pot already
    # Lock it in and go to showdown
    if distance <= 3 and game.pot > game.min_bet * 10:
        # 30% chance to hermit with strong hand and big pot
        import random
        if random.random() < 0.3:
            return True

    return False


def should_play_chariot(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play The Chariot (Trionfo VII) to force discards.

    Play it when:
    - AI has a strong hand
    - Opponents have multiple cards (weakening them helps)
    - Want to force opponents to discard their best cards

    Returns:
        True if AI should play The Chariot
    """
    from sabacc_game import calculate_hand_value

    # Get active opponents
    active_opponents = [p for p in game.players
                       if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not active_opponents:
        return False

    # Check AI's hand strength
    value, is_busted = calculate_hand_value(player.hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')

    # Only play if AI has good hand (distance <= 7)
    if distance > 7:
        return False

    # Count opponents with multiple cards
    multi_card_opponents = sum(1 for opp in active_opponents if len(opp.hand) > 2)

    # Play if multiple opponents have many cards
    if multi_card_opponents >= 2:
        return True

    # Play if facing one opponent with lots of cards and AI has strong hand
    if multi_card_opponents >= 1 and distance <= 3:
        return True

    return False


def should_play_hierophant(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play The Hierophant (Trionfo V) to force reveals.

    Play it when:
    - Facing aggressive opponents (high bluff frequency)
    - AI has a strong hand and suspects bluffs
    - Want to expose weak hands and force folds

    Returns:
        True if AI should play The Hierophant
    """
    from sabacc_game import calculate_hand_value

    # Get active opponents
    active_opponents = [p for p in game.players
                       if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not active_opponents:
        return False

    # Check AI's hand strength
    value, is_busted = calculate_hand_value(player.hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')

    # Only play if AI has decent hand (otherwise revealing helps opponents)
    if distance > 10:
        return False

    # Analyze opponents for aggression
    aggressive_count = 0
    loose_count = 0

    for opp in active_opponents:
        model = get_opponent_model(opp.name)
        if model.is_aggressive_player():
            aggressive_count += 1
        if model.is_loose_player():
            loose_count += 1

    # Play if multiple aggressive opponents (likely bluffing)
    if aggressive_count >= 2:
        return True

    # Play if facing loose aggressive opponent with good hand
    if aggressive_count >= 1 and distance <= 7:
        return True

    # Play if multiple loose players (weak hands) and AI has strong hand
    if loose_count >= 2 and distance <= 5:
        return True

    return False


def should_play_emperor(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play The Emperor (Trionfo IV) to pressure an opponent.

    Play it when:
    - There are opponents who can be pressured
    - AI wants to force weak opponents to fold
    - AI wants to weaken strong opponents

    Returns:
        True if AI should play The Emperor
    """
    # Get valid targets
    targets = [p for p in game.players
               if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not targets:
        return False

    # Play if there are multiple opponents (maximize pressure)
    if len(targets) >= 2:
        return True

    # Play against a single opponent if they seem weak (low credits)
    if len(targets) == 1:
        target = targets[0]
        if target.credits < game.min_bet * 3:  # Low on chips
            return True

    return False


def choose_emperor_target(game: GameState, player: Player) -> 'Player':
    """
    Choose which opponent to target with The Emperor.

    Strategy:
    - Target player with lowest credits (they might fold)
    - Or target strongest hand if we know their tendencies (from opponent modeling)

    Args:
        game: Current game state
        player: The AI player

    Returns:
        The chosen target player
    """
    import random

    targets = [p for p in game.players
               if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not targets:
        return None

    # Strategy 1: Target player with fewest credits (most likely to fold)
    targets_by_credits = sorted(targets, key=lambda p: p.credits)

    # 70% chance to target weakest stack
    if random.random() < 0.7:
        return targets_by_credits[0]

    # 30% chance to target a random player (unpredictable)
    return random.choice(targets)


def should_play_magician(game: GameState, player: Player) -> bool:
    """
    Decide if AI should play The Magician (Trionfo I) to arrange top 4 cards.

    Play it when:
    - AI's hand needs improvement (distance > 8)
    - AI hasn't drawn yet this turn (can benefit from arranged cards)
    - Early in the hand (more draws to come)

    Returns:
        True if AI should play The Magician
    """
    from sabacc_game import calculate_hand_value

    value, is_busted = calculate_hand_value(player.hand)
    distance = abs(abs(value) - 23) if not is_busted else float('inf')

    # Don't play if hand is already good
    if distance <= 5:
        return False

    # Don't play if we already drew this turn (can't benefit immediately)
    if player.has_drawn:
        return False

    # Play if hand needs improvement
    if distance > 8:
        return True

    return False


def arrange_magician_cards(game: GameState, player: Player, top_4_cards: list) -> list:
    """
    Arrange the top 4 cards optimally for The Magician effect.

    Strategy:
    - Evaluate which cards help our hand
    - Put best cards on top (we'll draw them)
    - Sort by how much each card improves our hand

    Args:
        game: Current game state
        player: The AI player
        top_4_cards: The 4 cards to arrange

    Returns:
        Arranged list of 4 cards (index 0 = top of deck)
    """
    from sabacc_game import calculate_hand_value

    current_value, current_busted = calculate_hand_value(player.hand)
    current_distance = abs(abs(current_value) - 23) if not current_busted else float('inf')

    # Score each card by how much it would improve our hand
    card_scores = []
    for card in top_4_cards:
        test_hand = player.hand + [card]
        test_value, test_busted = calculate_hand_value(test_hand)
        test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

        # Lower distance is better, so improvement is negative delta
        improvement = current_distance - test_distance
        card_scores.append((card, improvement))

    # Sort by improvement (best first)
    card_scores.sort(key=lambda x: x[1], reverse=True)

    # Return cards in order: best on top
    return [card for card, score in card_scores]


def estimate_win_probability(distance_to_23):
    """
    Estimate the probability of winning based on distance from 23.

    This is a rough heuristic based on the assumption that:
    - Closer to 23 = higher chance to win
    - Perfect hand (distance 0) still only ~90% win rate (can lose to ties)
    - Very bad hands (distance 15+) have very low win rates

    Args:
        distance_to_23: How far the hand is from 23

    Returns:
        Estimated win probability (0.0 to 1.0)
    """
    if distance_to_23 == 0:
        return 0.90  # Perfect hand, but could still lose to ties

    if distance_to_23 <= 2:
        return 0.80  # Excellent hand

    if distance_to_23 <= 5:
        return 0.65  # Good hand

    if distance_to_23 <= 8:
        return 0.45  # Decent hand

    if distance_to_23 <= 12:
        return 0.25  # Mediocre hand

    if distance_to_23 <= 16:
        return 0.12  # Weak hand

    return 0.05  # Very weak hand


def evaluate_community_swaps(hand, community_cards):
    """
    Evaluate all possible swaps between hand cards and community cards.

    A swap means: give one card from hand, take one card from community.
    All community cards are visible to the player.

    Args:
        hand: The player's current hand
        community_cards: The visible community cards

    Returns:
        (hand_index, community_index, expected_distance) tuple, or None if no beneficial swap
    """
    if not community_cards or not hand:
        return None

    current_value, current_busted = calculate_hand_value(hand)
    current_distance = abs(abs(current_value) - 23) if not current_busted else float('inf')

    best_hand_idx = None
    best_comm_idx = None
    best_distance = current_distance

    # Try every possible swap
    for hand_idx in range(len(hand)):
        for comm_idx in range(len(community_cards)):
            # Simulate the swap
            simulated_hand = hand.copy()
            card_to_remove = simulated_hand[hand_idx]
            card_to_add = community_cards[comm_idx]

            # Perform swap
            simulated_hand[hand_idx] = card_to_add

            # Evaluate new hand
            test_value, test_busted = calculate_hand_value(simulated_hand)
            test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

            # Is this swap better than what we have?
            if test_distance < best_distance:
                best_distance = test_distance
                best_hand_idx = hand_idx
                best_comm_idx = comm_idx

    if best_hand_idx is not None:
        return (best_hand_idx, best_comm_idx, best_distance)

    return None


def evaluate_discard_pile_draws(hand, discard_pile):
    """
    Evaluate all possible draws from the discard pile.

    Remember: drawing from index i means taking card[i] and all cards above it (higher indices).
    All discard pile cards are visible to the player.

    Args:
        hand: The player's current hand
        discard_pile: The visible discard pile (index 0 = oldest/bottom)

    Returns:
        (best_index, expected_distance) tuple, or None if no beneficial draw exists
    """
    if not discard_pile:
        return None

    current_value, current_busted = calculate_hand_value(hand)
    current_distance = abs(abs(current_value) - 23) if not current_busted else float('inf')

    best_draw_index = None
    best_expected_distance = current_distance

    # Try each possible draw from the discard pile
    # Index i means: take card[i], card[i+1], ..., card[len-1]
    for draw_index in range(len(discard_pile)):
        # Cards we would take (draw_index and everything above it)
        cards_to_take = discard_pile[draw_index:]

        # Simulate adding these cards to our hand
        simulated_hand = hand + cards_to_take

        # Calculate value with new cards
        test_value, test_busted = calculate_hand_value(simulated_hand)
        test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

        # Now, if we took multiple cards, we might want to discard some
        # Simulate optimal discarding to see the best possible outcome
        if len(simulated_hand) > 2:
            # Try to optimize by discarding worst cards
            # We can discard back down to 2 cards if we want
            best_distance_after_discard = test_distance

            # Try discarding 1, 2, or 3 cards to see if it helps
            for num_discards in range(1, min(4, len(simulated_hand) - 1)):
                optimized_hand = optimize_hand_by_discarding(simulated_hand, num_discards)
                if optimized_hand:
                    opt_value, opt_busted = calculate_hand_value(optimized_hand)
                    opt_distance = abs(abs(opt_value) - 23) if not opt_busted else float('inf')
                    best_distance_after_discard = min(best_distance_after_discard, opt_distance)

            test_distance = best_distance_after_discard

        # Is this draw better than what we have now?
        if test_distance < best_expected_distance:
            best_expected_distance = test_distance
            best_draw_index = draw_index

    if best_draw_index is not None:
        return (best_draw_index, best_expected_distance)

    return None


def optimize_hand_by_discarding(hand, num_to_discard):
    """
    Find the best hand possible by discarding num_to_discard cards.

    Args:
        hand: Current hand
        num_to_discard: How many cards to discard

    Returns:
        Optimized hand (with cards removed), or None if not possible
    """
    if num_to_discard >= len(hand):
        return None

    if num_to_discard == 0:
        return hand

    # For small numbers, try all combinations
    from itertools import combinations

    best_hand = None
    best_distance = float('inf')

    # Generate all possible hands by removing num_to_discard cards
    hand_size_after = len(hand) - num_to_discard

    for kept_cards in combinations(hand, hand_size_after):
        test_hand = list(kept_cards)
        test_value, test_busted = calculate_hand_value(test_hand)
        test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

        if test_distance < best_distance:
            best_distance = test_distance
            best_hand = test_hand

    return best_hand


def find_worst_card_to_discard(hand) -> int:
    """
    Find the card that, when removed, gets us closest to 23.

    Args:
        hand: The player's current hand

    Returns:
        Index of the worst card to discard, or None if no good discard
    """
    current_value, current_busted = calculate_hand_value(hand)
    current_distance = abs(abs(current_value) - 23) if not current_busted else float('inf')

    best_discard_index = None
    best_distance_after_discard = current_distance

    # Try discarding each card and see which gives the best result
    for i in range(len(hand)):
        # Create a copy of hand without this card
        test_hand = hand[:i] + hand[i+1:]

        if len(test_hand) == 0:  # Don't discard if it leaves us with no cards
            continue

        test_value, test_busted = calculate_hand_value(test_hand)
        test_distance = abs(abs(test_value) - 23) if not test_busted else float('inf')

        # If discarding this card improves our distance to 23, remember it
        if test_distance < best_distance_after_discard:
            best_distance_after_discard = test_distance
            best_discard_index = i

    return best_discard_index


def should_play_hanged_man(game: GameState, hanged_man_player: Player, acting_player: Player, trionfi) -> bool:
    """
    Decide whether to play The Hanged Man to nullify an opponent's Trionfi effect.

    Args:
        game: The current game state
        hanged_man_player: The player who has The Hanged Man
        acting_player: The player who is playing the Trionfi effect
        trionfi: The TrionfiEffect object being played

    Returns:
        True if The Hanged Man should be played, False otherwise
    """
    # Get our hand evaluation
    our_value, our_busted = calculate_hand_value(hanged_man_player.hand)
    our_distance = abs(abs(our_value) - 23) if not our_busted else float('inf')

    # Trionfi that directly target/harm players - high priority to block
    targeted_effects = {
        4,   # The Emperor - forces ante/discard/fold, likely targets us
        5,   # The Hierophant - forces reveal or fold
        7,   # The Chariot - forces discard or fold
    }

    # Powerful beneficial effects that can swing the game
    powerful_beneficial = {
        1,   # The Magician - rearranges deck
        10,  # Wheel of Fortune - draw 4, keep what you want
    }

    # Moderate effects - consider blocking based on game state
    moderate_effects = {
        9,   # The Hermit - withdraw from betting
    }

    # Always block targeted effects (they likely harm us)
    if trionfi.number in targeted_effects:
        # Block with 80% probability (some randomness to avoid predictability)
        return random.random() < 0.8

    # Block powerful beneficial effects if opponent is in a weak position
    # (they're trying to recover/improve)
    if trionfi.number in powerful_beneficial:
        # If opponent seems desperate (low credits, likely weak hand based on betting)
        if acting_player.credits < game.min_bet * 10:  # Very low on credits
            # Block with 70% probability
            return random.random() < 0.7

        # If we're in a strong position (good hand, good credits)
        if our_distance <= 5 and hanged_man_player.credits > game.pot:
            # Block with 50% probability to prevent opponent improvement
            return random.random() < 0.5

        # Otherwise, don't waste The Hanged Man
        return False

    # For moderate effects, rarely block (save The Hanged Man for important moments)
    if trionfi.number in moderate_effects:
        # Only block 10% of the time
        return random.random() < 0.1

    # For other effects, don't waste The Hanged Man
    return False


def should_give_away_devil(game: GameState, player: Player) -> bool:
    """
    Decide whether to give away The Devil card.

    Args:
        game: The current game state
        player: The player who has The Devil

    Returns:
        True if should give away The Devil, False otherwise
    """
    # The Devil is -15 points, which is terrible for your hand
    # Almost always give it away!

    # Calculate our current hand value with The Devil
    our_value, our_busted = calculate_hand_value(player.hand)

    # Try removing The Devil and see if it helps
    hand_without_devil = [c for c in player.hand if c != ('15', 'T')]
    value_without, busted_without = calculate_hand_value(hand_without_devil)

    distance_with = abs(abs(our_value) - 23) if not our_busted else float('inf')
    distance_without = abs(abs(value_without) - 23) if not busted_without else float('inf')

    # If removing The Devil improves our distance, give it away
    if distance_without < distance_with:
        return True

    # Edge case: if The Devil somehow helps us (rare symmetric case where -15 helps),
    # still give it away 50% of the time to avoid being predictable
    return random.random() < 0.5


def should_play_universe(game: GameState, player: Player) -> bool:
    """
    Decide whether to play The Universe to see the top 6 cards of the draw pile.

    Strategy: Play when you're likely to draw from the draw pile and want
    to know what's coming.

    Args:
        game: The current game state
        player: The player who has The Universe

    Returns:
        True if should play The Universe, False otherwise
    """
    # Check if there are enough cards in draw pile
    if len(game.draw_pile.cards) < 6:
        return False

    our_value, our_busted = calculate_hand_value(player.hand)
    our_distance = abs(abs(our_value) - 23) if not our_busted else float('inf')

    # Only valuable if we're likely to draw from the draw pile
    # Play more often if hand is weak/moderate and we haven't drawn yet
    if not player.has_drawn:
        # Weak hand (distance > 8) - likely to draw, information is valuable
        if our_distance > 8 or our_busted:
            # Play 40% of the time with weak hand (helps decide if draw pile is good)
            return random.random() < 0.4

        # Moderate hand (distance 5-8) - might draw
        if 5 < our_distance <= 8:
            # Play 20% of the time with moderate hand
            return random.random() < 0.2

        # Strong hand (distance <= 5) - unlikely to draw, less valuable
        # Play 5% of the time (might still be useful to know what opponents could draw)
        return random.random() < 0.05
    else:
        # Already drawn - information is less valuable
        # Only play 10% of the time to see what opponents might draw
        return random.random() < 0.1


def should_play_judgment(game: GameState, player: Player) -> bool:
    """
    Decide whether to play The Last Judgment to immediately end the hand.

    Strategy: Play when you have a strong hand and want to prevent opponents
    from drawing cards to improve.

    Args:
        game: The current game state
        player: The player who has The Last Judgment

    Returns:
        True if should play The Last Judgment, False otherwise
    """
    our_value, our_busted = calculate_hand_value(player.hand)
    our_distance = abs(abs(our_value) - 23) if not our_busted else float('inf')

    # Never play if we're busted or have a weak hand
    if our_busted or our_distance > 7:
        return False

    # Strong hand (distance <= 3): very likely to play
    # Lock in the win before opponents can improve
    if our_distance <= 3:
        # Consider pot size - only worth it if pot is significant
        if game.pot >= game.min_bet * 5:
            # Play 70% of the time with strong hand and good pot
            return random.random() < 0.7
        else:
            # Smaller pot, play less often
            return random.random() < 0.3

    # Good hand (distance 4-7): sometimes play
    # Depends on pot size and opponent count
    if our_distance <= 7:
        active_opponents = [p for p in game.players if p != player and not p.has_folded]

        # More opponents = more likely someone could improve
        # Play more often with more opponents
        if len(active_opponents) >= 3:
            # Multiple opponents, higher chance someone improves
            if game.pot >= game.min_bet * 5:
                return random.random() < 0.4
        elif len(active_opponents) == 2:
            if game.pot >= game.min_bet * 5:
                return random.random() < 0.2

    return False


def should_play_sun(game: GameState, player: Player) -> bool:
    """
    Decide whether to play The Sun to force all hands face up.

    Strategy: Play when you have a strong hand to prevent bluffing

    Args:
        game: The current game state
        player: The player who has The Sun

    Returns:
        True if should play The Sun, False otherwise
    """
    # Don't play if hands are already face up
    if game.hands_face_up:
        return False

    our_value, our_busted = calculate_hand_value(player.hand)
    our_distance = abs(abs(our_value) - 23) if not our_busted else float('inf')

    # Only play if we have a strong hand (distance <= 5)
    # Playing with a weak hand reveals our weakness
    if our_distance > 5 or our_busted:
        return False

    # Check if there are aggressive opponents who might be bluffing
    active_opponents = [p for p in game.players if p != player and not p.has_folded]
    if not active_opponents:
        return False

    # Check opponent aggression
    avg_aggression = 0.5
    if active_opponents:
        from sabacc_ai import get_opponent_model
        aggression_values = [get_opponent_model(p.name).get_aggression_factor()
                           for p in active_opponents]
        if aggression_values:
            avg_aggression = sum(aggression_values) / len(aggression_values)

    # Play more often vs aggressive opponents (they might be bluffing)
    if avg_aggression > 0.6:
        # Play 60% of time vs aggressive opponents
        return random.random() < 0.6
    elif avg_aggression > 0.4:
        # Play 30% of time vs moderate opponents
        return random.random() < 0.3
    else:
        # Play 10% of time vs passive opponents (less bluffing expected)
        return random.random() < 0.1


def should_play_moon(game: GameState, player: Player) -> bool:
    """
    Decide whether to play The Moon to add another community card.

    Strategy: Play when hand is weak and need more swap options

    Args:
        game: The current game state
        player: The player who has The Moon

    Returns:
        True if should play The Moon, False otherwise
    """
    our_value, our_busted = calculate_hand_value(player.hand)
    our_distance = abs(abs(our_value) - 23) if not our_busted else float('inf')

    # If hand is weak (distance > 8) or busted, adding more community cards helps
    if our_distance > 8 or our_busted:
        # Play 70% of the time when weak
        return random.random() < 0.7

    # If hand is moderate (distance 5-8), sometimes play for more options
    if 5 < our_distance <= 8:
        # Play 30% of the time
        return random.random() < 0.3

    # If hand is strong (distance <= 5), rarely play The Moon
    # (don't need more options, current hand is good)
    return random.random() < 0.1


def choose_devil_target(game: GameState, player: Player, eligible_targets: list) -> Player:
    """
    Choose which player to give The Devil card to.

    Strategy: Give it to the player who is doing best (most credits, or appears strongest)

    Args:
        game: The current game state
        player: The player giving away The Devil
        eligible_targets: List of players who can receive The Devil

    Returns:
        The chosen target player
    """
    # Strategy: Give it to the player with the most credits (they're winning)
    # This helps level the playing field

    # If we have opponent models, consider aggression/strength
    # For now, target the richest player

    richest_player = max(eligible_targets, key=lambda p: p.credits)

    # Add some randomness (70% target richest, 30% random)
    if random.random() < 0.7:
        return richest_player
    else:
        return random.choice(eligible_targets)