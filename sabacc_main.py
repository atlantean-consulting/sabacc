#!/usr/bin/env python3
"""
Sabacc con i Tarocchi - Main Game Loop and User Interface
"""

from sabacc_game import GameState, Player, calculate_hand_value, get_random_opponent_names
from sabacc_ai import get_simple_ai_action

def get_player_action_interactive(game: GameState, player: Player) -> dict:
    """
    Get action from a human player through interactive prompts.

    Args:
        game: The current game state
        player: The human player making the decision

    Returns:
        Action dictionary for execute_player_turn
    """
    action = {}

    # Show player their current state
    value, busted = calculate_hand_value(player.hand)
    status = "BUSTED" if busted else "OK"
    print(f"\nYour hand: {player.hand}")
    print(f"Hand value: {value} [{status}]")
    print(f"Your credits: {player.credits}")
    print(f"Current bet: {player.current_bet}")
    print(f"Amount to call: {game.current_bet - player.current_bet}")
    print(f"Pot: {game.pot}")

    # Show community cards
    print(f"Community cards: {game.community_cards}")

    # Get betting action
    amount_to_call = game.current_bet - player.current_bet

    if amount_to_call > 0:
        print(f"\nBetting options: (f)old, (c)all {amount_to_call}, (r)aise")
    else:
        print(f"\nBetting options: (f)old, (c)heck, (r)aise")

    bet_choice = input("Your choice: ").strip().lower()

    if bet_choice == 'f':
        action['bet_action'] = 'fold'
        return action  # No more actions if folding

    elif bet_choice == 'c':
        action['bet_action'] = 'call'

    elif bet_choice == 'r':
        action['bet_action'] = 'raise'
        while True:
            try:
                raise_amount = int(input(f"Raise amount (min {game.min_bet}): "))
                if raise_amount >= game.min_bet:
                    action['raise_amount'] = raise_amount
                    break
                else:
                    print(f"Raise must be at least {game.min_bet}")
            except ValueError:
                print("Please enter a valid number")
    else:
        # Default to call if invalid input
        action['bet_action'] = 'call'

        # Check if player has any playable Trionfi
        from sabacc_trionfi import get_playable_trionfi
        playable_trionfi = get_playable_trionfi(player)

        if playable_trionfi:
            print("\nYou have special cards you can play:")
            for i, (card, trionfi) in enumerate(playable_trionfi):
                print(f"  {i}: {trionfi.name} - {trionfi.description}")
            print(f"  s: Skip playing special cards")

            special_choice = input("Play a special card? ").strip().lower()

            if special_choice != 's':
                try:
                    idx = int(special_choice)
                    if 0 <= idx < len(playable_trionfi):
                        card, trionfi = playable_trionfi[idx]
                        action['play_trionfi'] = card
                except ValueError:
                    pass

    # Get drawing action (if not already drawn)
    if not player.has_drawn:
        print("\nDrawing options:")
        print("  (1) Draw from draw pile")
        if game.discard_pile:
            print(f"  (2) Draw from discard pile: {game.discard_pile}")
        print(f"  (3) Swap with community cards: {game.community_cards}")
        print("  (s) Skip drawing")

        draw_choice = input("Your choice: ").strip().lower()

        if draw_choice == '1':
            action['draw_action'] = 'draw_pile'

        elif draw_choice == '2' and game.discard_pile:
            print("Which card? (0 = oldest/bottom)")
            for i, card in enumerate(game.discard_pile):
                print(f"  {i}: {card}")
            while True:
                try:
                    idx = int(input("Index: "))
                    if 0 <= idx < len(game.discard_pile):
                        action['draw_action'] = 'discard_pile'
                        action['draw_index'] = idx
                        break
                    else:
                        print("Invalid index")
                except ValueError:
                    print("Please enter a valid number")

        elif draw_choice == '3':
            # Swap with community
            print("Which card from your hand to swap?")
            for i, card in enumerate(player.hand):
                print(f"  {i}: {card}")
            while True:
                try:
                    hand_idx = int(input("Hand card index: "))
                    if 0 <= hand_idx < len(player.hand):
                        break
                    else:
                        print("Invalid index")
                except ValueError:
                    print("Please enter a valid number")

            print("Which community card to take?")
            for i, card in enumerate(game.community_cards):
                print(f"  {i}: {card}")
            while True:
                try:
                    comm_idx = int(input("Community card index: "))
                    if 0 <= comm_idx < len(game.community_cards):
                        break
                    else:
                        print("Invalid index")
                except ValueError:
                    print("Please enter a valid number")

            action['draw_action'] = 'community'
            action['hand_card_index'] = hand_idx
            action['community_card_index'] = comm_idx

    # Note: We'll ask about discarding AFTER the draw happens
    # Set a flag to indicate we need to ask about discarding later
    action['ask_discard_after_draw'] = True

    return action

def play_game():
    """
    Main game loop - play hands until game is over.
    Game ends when:
    - Only one player has credits remaining
    - Human player runs out of credits
    - Human player chooses to quit
    """
    print("\n" + "=" * 60)
    print("SABACC CON I TAROCCHI")
    print("=" * 60)

    # Get player setup
    player_name = input("\nWhat is your name? ").strip() or "Player"

    num_opponents = 3
    try:
        num_input = input("How many opponents (1-5)? [3]: ").strip()
        if num_input:
            num_opponents = int(num_input)
            num_opponents = max(1, min(5, num_opponents))
    except ValueError:
        pass

    opponent_names = get_random_opponent_names(num_opponents)
    game = GameState([player_name] + opponent_names, starting_credits=500, min_bet=2)

    print(f"\nPlayers: {', '.join([p.name for p in game.players])}")
    print(f"Starting credits: {game.players[0].credits}")
    print(f"Minimum bet: {game.min_bet}")
    print("\n" + "=" * 60)

    while True:
        # Check if game should end
        players_with_credits = [p for p in game.players if p.credits > 0]

        if len(players_with_credits) <= 1:
            print("\n" + "=" * 60)
            print("GAME OVER")
            print("=" * 60)
            if len(players_with_credits) == 1:
                winner = players_with_credits[0]
                print(f"\n🏆 {winner.name} is the last player standing with {winner.credits} credits!")
            else:
                print("\nEveryone is out of credits!")
            break

        # Check if human player is out
        human_player = game.players[0]
        if human_player.credits <= 0:
            print("\n" + "=" * 60)
            print("GAME OVER")
            print("=" * 60)
            print(f"\n{human_player.name} is out of credits!")
            break

        # Ask human player if they want to continue (unless this is the first hand)
        if game.hand_number > 0 and human_player.is_human:
            continue_choice = input("\nPlay another hand? (y/n): ").strip().lower()
            if continue_choice != 'y':
                print("\n" + "=" * 60)
                print("GAME OVER - Player quit")
                print("=" * 60)
                print("\nFinal standings:")
                sorted_players = sorted(game.players, key=lambda p: p.credits, reverse=True)
                for i, p in enumerate(sorted_players, 1):
                    print(f"  {i}. {p.name}: {p.credits} credits")
                break

        # Play a hand
        game.play_hand(get_ai_action_func=get_simple_ai_action)

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    play_game()