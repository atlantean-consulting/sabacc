#!/usr/bin/env python3
"""
Sabacc con i Tarocchi - Trionfi (Trump) Special Effects
"""

from typing import Callable, Optional
from sabacc_game import GameState, Player, Card


class TrionfiEffect:
    """Represents a Trionfi card with a special effect"""

    def __init__(self, number: int, name: str, description: str,
                 effect: Optional[Callable] = None,
                 can_play_anytime: bool = False,
                 stays_in_hand: bool = False):
        """
        Args:
            number: The Trionfi number (0-21)
            name: The name of the card
            description: Description of the effect
            effect: The function that implements the effect
            can_play_anytime: If True, can be played even when not your turn
            stays_in_hand: If True, card stays in hand after using effect
        """
        self.number = number
        self.name = name
        self.description = description
        self.effect = effect
        self.can_play_anytime = can_play_anytime
        self.stays_in_hand = stays_in_hand

    def apply_effect(self, game: GameState, player: Player) -> None:
        """Apply the card's special effect"""
        if self.effect:
            self.effect(game, player)

            # Remove card from hand unless it stays
            if not self.stays_in_hand:
                card = (str(self.number), 'T')
                if card in player.hand:
                    player.hand.remove(card)
                    game.removed_pile.append(card)


# === TRIONFI EFFECT IMPLEMENTATIONS ===

def magician_effect(game: GameState, player: Player) -> None:
    """
    Trionfo I - The Magician
    Alter the Future: Take the top 4 cards from the draw pile,
    arrange them to your liking, and replace them on top.
    """
    print(f"\n✨ {player.name} plays The Magician - Alter the Future!")

    if len(game.draw_pile.cards) < 4:
        print("Not enough cards in draw pile to use this effect.")
        return

    # Take top 4 cards
    top_4 = [game.draw_pile.cards.pop(0) for _ in range(4)]

    if player.is_human:
        print(f"\nTop 4 cards: {top_4}")
        print("Enter the order you want (0-3), separated by spaces:")
        print("Example: 3 1 0 2 would put card 3 on top, then 1, then 0, then 2 on bottom")

        while True:
            try:
                order_input = input("Order: ").strip().split()
                order = [int(x) for x in order_input]
                if len(order) == 4 and all(0 <= x < 4 for x in order) and len(set(order)) == 4:
                    reordered = [top_4[i] for i in order]
                    break
                else:
                    print("Invalid order. Use four unique numbers 0-3.")
            except (ValueError, IndexError):
                print("Invalid input. Try again.")

        # Put cards back in specified order
        for card in reversed(reordered):
            game.draw_pile.cards.insert(0, card)

        print(f"Cards rearranged. New top card: {game.draw_pile.cards[0]}")
    else:
        # AI arranges cards strategically
        from sabacc_ai import arrange_magician_cards
        arranged = arrange_magician_cards(game, player, top_4)

        # Put cards back in arranged order (best on top)
        for card in reversed(arranged):
            game.draw_pile.cards.insert(0, card)

        print(f"{player.name} rearranged the top 4 cards strategically.")


def emperor_effect(game: GameState, player: Player) -> None:
    """
    Trionfo IV - The Emperor
    A player of your choice must either ante up an additional big blind,
    immediately discard 2 cards, or fold.
    """
    print(f"\n👑 {player.name} plays The Emperor!")

    # Get list of other active players
    targets = [p for p in game.players
               if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

    if not targets:
        print("No valid targets for The Emperor's effect.")
        return

    if player.is_human:
        print("\nChoose a player to target:")
        for i, p in enumerate(targets):
            print(f"  {i}: {p.name}")

        while True:
            try:
                idx = int(input("Target: "))
                if 0 <= idx < len(targets):
                    target = targets[idx]
                    break
                else:
                    print("Invalid selection")
            except ValueError:
                print("Please enter a valid number")
    else:
        # AI picks strategically
        from sabacc_ai import choose_emperor_target
        target = choose_emperor_target(game, player)

    print(f"\n{player.name} targets {target.name}!")

    # Target must choose
    if target.is_human:
        print(f"\n{target.name}, you must choose:")
        print(f"  (1) Ante up an additional {game.min_bet} credits")
        print(f"  (2) Discard 2 cards immediately")
        print(f"  (3) Fold")

        choice = input("Your choice: ").strip()

        if choice == '1':
            if target.credits >= game.min_bet:
                target.credits -= game.min_bet
                game.pot += game.min_bet
                print(f"{target.name} antes up {game.min_bet} credits.")
            else:
                print(f"{target.name} doesn't have enough credits and must fold!")
                game.player_fold(target)

        elif choice == '2':
            if len(target.hand) >= 2:
                print(f"Your hand: {target.hand}")
                discarded = []
                for i in range(2):
                    print(f"Discard card {i + 1} of 2:")
                    for j, card in enumerate(target.hand):
                        if card not in discarded:
                            print(f"  {j}: {card}")
                    while True:
                        try:
                            idx = int(input("Index: "))
                            if 0 <= idx < len(target.hand) and target.hand[idx] not in discarded:
                                discarded.append(target.hand[idx])
                                break
                        except (ValueError, IndexError):
                            print("Invalid selection")

                for card in discarded:
                    target.hand.remove(card)
                    game.discard_pile.append(card)
                print(f"{target.name} discarded {discarded}")
            else:
                print(f"{target.name} doesn't have 2 cards and must fold!")
                game.player_fold(target)

        else:
            game.player_fold(target)

    else:
        # AI logic: fold if weak hand, ante if strong, discard if medium
        from sabacc_game import calculate_hand_value
        value, busted = calculate_hand_value(target.hand)

        if busted or abs(value) < 10:
            game.player_fold(target)
            print(f"{target.name} folds.")
        elif target.credits >= game.min_bet and abs(value) >= 18:
            target.credits -= game.min_bet
            game.pot += game.min_bet
            print(f"{target.name} antes up {game.min_bet} credits.")
        else:
            if len(target.hand) >= 2:
                # Discard 2 lowest cards
                import random
                to_discard = random.sample(target.hand, 2)
                for card in to_discard:
                    target.hand.remove(card)
                    game.discard_pile.append(card)
                print(f"{target.name} discarded 2 cards.")
            else:
                game.player_fold(target)
                print(f"{target.name} folds.")


def hierophant_effect(game: GameState, player: Player) -> None:
    """
    Trionfo V - The Hierophant
    Everyone must either disclose the current value of their hand or instantly fold.
    """
    print(f"\n⛪ {player.name} plays The Hierophant!")
    print("All players must reveal their hand values or fold!")

    from sabacc_game import calculate_hand_value

    for p in game.players:
        if p == player or p.has_folded or getattr(p, 'is_hermit', False):
            continue

        if p.is_human:
            choice = input(f"\n{p.name}, reveal your hand value? (y/n): ").strip().lower()
            if choice == 'y':
                value, busted = calculate_hand_value(p.hand)
                status = "BUSTED" if busted else "OK"
                print(f"{p.name}'s hand value: {value} [{status}]")
            else:
                game.player_fold(p)
                print(f"{p.name} folds rather than reveal.")
        else:
            # AI: reveal if hand is decent, fold if terrible
            value, busted = calculate_hand_value(p.hand)
            if busted or abs(value) < 8:
                game.player_fold(p)
                print(f"{p.name} folds rather than reveal.")
            else:
                status = "BUSTED" if busted else "OK"
                print(f"{p.name} reveals hand value: {value} [{status}]")


def chariot_effect(game: GameState, player: Player) -> None:
    """
    Trionfo VII - The Chariot
    Everyone must either discard 1 card or instantly fold.
    """
    print(f"\n🏇 {player.name} plays The Chariot!")
    print("All players must discard 1 card or fold!")

    for p in game.players:
        if p == player or p.has_folded or getattr(p, 'is_hermit', False):
            continue

        if p.is_human:
            if len(p.hand) == 0:
                game.player_fold(p)
                print(f"{p.name} has no cards and must fold!")
                continue

            choice = input(f"\n{p.name}, discard a card? (y/n): ").strip().lower()
            if choice == 'y':
                print(f"Your hand: {p.hand}")
                while True:
                    try:
                        idx = int(input("Which card to discard? "))
                        if 0 <= idx < len(p.hand):
                            card = p.hand.pop(idx)
                            game.discard_pile.append(card)
                            print(f"{p.name} discarded {card}")
                            break
                    except (ValueError, IndexError):
                        print("Invalid selection")
            else:
                game.player_fold(p)
                print(f"{p.name} folds rather than discard.")
        else:
            # AI: fold if hand is empty or terrible, otherwise discard worst card
            from sabacc_game import calculate_hand_value
            if len(p.hand) == 0:
                game.player_fold(p)
                print(f"{p.name} has no cards and must fold!")
            else:
                value, busted = calculate_hand_value(p.hand)
                if busted or abs(value) < 8:
                    game.player_fold(p)
                    print(f"{p.name} folds rather than discard.")
                else:
                    # Discard worst card strategically
                    from sabacc_ai import find_worst_card_to_discard
                    worst_idx = find_worst_card_to_discard(p.hand)

                    if worst_idx is not None:
                        card = p.hand.pop(worst_idx)
                    else:
                        # Fallback to random if no worst card found
                        import random
                        card = p.hand.pop(random.randint(0, len(p.hand) - 1))

                    game.discard_pile.append(card)
                    print(f"{p.name} discarded a card.")


def hermit_effect(game: GameState, player: Player) -> None:
    """
    Trionfo IX - The Hermit
    Place the Hermit card face up in front of you.
    You take no further action in the hand and automatically advance to the showdown
    without having to bet again. You are also immune from any special effects during this time.
    """
    print(f"\n🧙 {player.name} plays The Hermit!")
    print(f"{player.name} withdraws from betting and will advance directly to showdown.")

    # Mark player as "hermit mode" - they're still in but can't be affected
    player.is_hermit = True


def wheel_of_fortune_effect(game: GameState, player: Player) -> None:
    """
    Trionfo X - Wheel of Fortune
    Draw 4 cards, keep what you want, and discard the rest.
    """
    print(f"\n🎡 {player.name} plays Wheel of Fortune!")

    game.ensure_cards_available(4)

    drawn_cards = []
    for _ in range(4):
        card = game.draw_pile.draw()
        drawn_cards.append(card)

    print(f"Drew 4 cards: {drawn_cards}")

    if player.is_human:
        # Remove Wheel of Fortune card from hand
        player.hand.remove(('10', 'T'))

        print(f"Your current hand: {player.hand}")
        print("Which cards do you want to keep? (Enter indices separated by spaces, or 'none')")
        for i, card in enumerate(drawn_cards):
            print(f"  {i}: {card}")

        keep_input = input("Keep: ").strip()

        if keep_input.lower() != 'none':
            try:
                keep_indices = [int(x) for x in keep_input.split()]
                kept_cards = [drawn_cards[i] for i in keep_indices if 0 <= i < 4]
                discarded_cards = [c for c in drawn_cards if c not in kept_cards]
            except (ValueError, IndexError):
                print("Invalid input, discarding all cards.")
                kept_cards = []
                discarded_cards = drawn_cards
        else:
            kept_cards = []
            discarded_cards = drawn_cards

        player.hand.extend(kept_cards)
        game.discard_pile.extend(discarded_cards)

        print(f"Kept: {kept_cards}")
        print(f"Discarded: {discarded_cards}")
    else:
        # AI chooses cards strategically
        from sabacc_ai import choose_wheel_of_fortune_cards

        # Remove Wheel of Fortune card from hand
        player.hand.remove(('10', 'T'))

        # Evaluate strategic choices with current hand
        current_hand = player.hand

        kept_cards = choose_wheel_of_fortune_cards(current_hand, drawn_cards)
        discarded_cards = [c for c in drawn_cards if c not in kept_cards]

        player.hand.extend(kept_cards)
        game.discard_pile.extend(discarded_cards)

        print(f"{player.name} kept {len(kept_cards)} card(s): {kept_cards}")
        if discarded_cards:
            print(f"{player.name} discarded {len(discarded_cards)} card(s): {discarded_cards}")


def hanged_man_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XII - The Hanged Man
    Can be played at any time during the hand, even if it is not your turn.
    Immediately nullifies the effect of whatever card preceded it.
    """
    print(f"\n🙃 {player.name} plays The Hanged Man - NOPE!")
    print("The previous card's effect is nullified!")

    # This needs special handling - it interrupts another effect
    # For now, just mark that it was played
    # The actual nullification logic will need to be in the game flow


def devil_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XV - The Devil
    If a player has the Devil card in their hand at the beginning of their turn,
    they can give the card to someone else.
    """
    print(f"\n😈 {player.name} plays The Devil!")

    targets = [p for p in game.players if p != player and not p.has_folded]

    if not targets:
        print("No one to give The Devil to!")
        return

    if player.is_human:
        print("Give The Devil to which player?")
        for i, p in enumerate(targets):
            print(f"  {i}: {p.name}")

        while True:
            try:
                idx = int(input("Target: "))
                if 0 <= idx < len(targets):
                    target = targets[idx]
                    break
            except ValueError:
                print("Invalid input")
    else:
        import random
        target = random.choice(targets)

    # Transfer the card
    devil_card = ('15', 'T')
    if devil_card in player.hand:
        player.hand.remove(devil_card)
        target.hand.append(devil_card)
        print(f"{player.name} gives The Devil to {target.name}!")


def moon_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XVIII - The Moon
    Give the Moon card to the dealer, who immediately deals another community card
    and removes the Moon card from play.
    """
    moon_card = ('18', 'T')

    print(f"\n🌙 {player.name} plays The Moon!")

    # Remove The Moon from player's hand
    if moon_card in player.hand:
        player.hand.remove(moon_card)
        game.removed_pile.append(moon_card)

    # Dealer deals another community card
    game.ensure_cards_available(1)
    new_card = game.draw_pile.draw()
    game.community_cards.append(new_card)

    print(f"Dealer adds {new_card} to the community cards.")
    print(f"Community cards are now: {game.community_cards}")


def sun_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XIX - The Sun
    Place the Sun card face up in front of you.
    Everyone must play with their hands face up for the remainder of the hand.
    """
    print(f"\n☀️ {player.name} plays The Sun!")
    print("All players must now play with their hands face up!")

    # Set a flag on the game state
    game.hands_face_up = True

    # Show all hands
    print("\n=== ALL HANDS REVEALED ===")
    for p in game.players:
        if not p.has_folded:
            from sabacc_game import calculate_hand_value
            value, busted = calculate_hand_value(p.hand)
            status = "BUSTED" if busted else "OK"
            print(f"{p.name}: {p.hand} = {value} [{status}]")
    print("=" * 50)


def judgment_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XX - The Last Judgment
    Immediately ends the hand and advances everyone to the showdown who has not already folded.
    """
    print(f"\n⚖️ {player.name} plays The Last Judgment!")
    print("The hand immediately ends and advances to showdown!")

    # Set a flag that will be checked in the game loop
    game.judgment_played = True


def universe_effect(game: GameState, player: Player) -> None:
    """
    Trionfo XXI - The Universe
    See the Future: Take the top 6 cards from the draw pile, look at them,
    and replace them in the same order without showing them to anyone else.
    The Universe card is then removed from the hand.
    """
    universe_card = ('21', 'T')

    print(f"\n🌌 {player.name} plays The Universe - See the Future!")

    # Remove The Universe from player's hand
    if universe_card in player.hand:
        player.hand.remove(universe_card)
        game.removed_pile.append(universe_card)

    if len(game.draw_pile.cards) < 6:
        print("Not enough cards in draw pile to use this effect.")
        return

    # Take top 6 cards
    top_6 = game.draw_pile.cards[:6]

    if player.is_human:
        print(f"\nTop 6 cards (in order from top to bottom): {top_6}")
        input("Press Enter to continue (don't show anyone!)...")
    else:
        print(f"{player.name} looks at the top 6 cards.")
        # AI could store this information for future decisions
        # For now, just acknowledge they've seen it

    # Cards stay in same order (already in the draw pile)


# === TRIONFI REGISTRY ===

TRIONFI_CARDS = {
    0: TrionfiEffect(0, "The Fool", "No special effect", None),
    1: TrionfiEffect(1, "The Magician", "Rearrange top 4 cards", magician_effect),
    2: TrionfiEffect(2, "The High Priestess", "-2 points", None),
    3: TrionfiEffect(3, "The Empress", "-3 points", None),
    4: TrionfiEffect(4, "The Emperor", "Target: ante, discard 2, or fold", emperor_effect),
    5: TrionfiEffect(5, "The Hierophant", "All reveal hand value or fold", hierophant_effect),
    6: TrionfiEffect(6, "The Lovers", "+6 or -6 points", None),  # Special: player chooses
    7: TrionfiEffect(7, "The Chariot", "All discard 1 or fold", chariot_effect),
    8: TrionfiEffect(8, "Strength", "-8 points", None),
    9: TrionfiEffect(9, "The Hermit", "Advance to showdown, immune to effects", hermit_effect, False, True),
    10: TrionfiEffect(10, "Wheel of Fortune", "Draw 4, keep what you want", wheel_of_fortune_effect),
    11: TrionfiEffect(11, "Justice", "-11 points", None),
    12: TrionfiEffect(12, "The Hanged Man", "NOPE card - nullify previous effect", hanged_man_effect, True),
    13: TrionfiEffect(13, "Death", "-13 points", None),
    14: TrionfiEffect(14, "Temperance", "-14 points", None),
    15: TrionfiEffect(15, "The Devil", "-15 points, can give to another player", devil_effect),
    16: TrionfiEffect(16, "The Tower", "-16 points", None),
    17: TrionfiEffect(17, "The Star", "-17 points", None),
    18: TrionfiEffect(18, "The Moon", "Dealer adds community card", moon_effect),
    19: TrionfiEffect(19, "The Sun", "All hands face up", sun_effect, False, True),
    20: TrionfiEffect(20, "The Last Judgment", "Immediately advance to showdown", judgment_effect),
    21: TrionfiEffect(21, "The Universe", "Look at top 6 cards", universe_effect),
}


def get_trionfi_effect(card: Card) -> Optional[TrionfiEffect]:
    """
    Get the Trionfi effect for a card, if it is a Trionfi.
    """
    rank, suit = card
    if suit == 'T':
        try:
            number = int(rank)
            return TRIONFI_CARDS.get(number)
        except ValueError:
            return None
    return None


def get_playable_trionfi(player: Player) -> list:
    """
    Get list of Trionfi cards in player's hand that have effects.
    """
    playable = []
    for card in player.hand:
        trionfi = get_trionfi_effect(card)
        if trionfi and trionfi.effect:
            playable.append((card, trionfi))
    return playable