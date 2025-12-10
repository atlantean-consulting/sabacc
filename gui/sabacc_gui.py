#!/usr/bin/env python3
"""
Sabacc con i Tarocchi - Tkinter GUI
Windows 95 Hearts-style interface
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import List, Optional
import os
import sys

# Add parent directory to path so we can import game modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sabacc_game import GameState, Player, Card, calculate_hand_value, get_random_opponent_names
from sabacc_ai import get_simple_ai_action
from sabacc_trionfi import get_playable_trionfi, get_trionfi_effect


class CardWidget:
    """Represents a visual card that can be clicked"""

    # Card dimensions
    CARD_WIDTH = 71
    CARD_HEIGHT = 96

    # Suit symbols (using Unicode)
    SUIT_SYMBOLS = {
        'W': '❧',  # Wands
        'C': '☋',  # Cups
        'S': '⚔',  # Swords
        'D': '☯',  # Disks
        'T': '✯'  # Trionfi
    }

    # Colors
    SUIT_COLORS = {
        'W': '#8B4513',  # Brown
        'C': '#4169E1',  # Blue
        'S': '#2F4F4F',  # Dark gray
        'D': '#FFD700',  # Gold
        'T': '#9370DB'  # Purple
    }

    # Image cache (class variable to persist across instances)
    _image_cache = {}
    _assets_path = None

    @classmethod
    def _get_assets_path(cls):
        """Get the path to the assets directory"""
        if cls._assets_path is None:
            # Get directory of this file (gui/sabacc_gui.py)
            gui_dir = os.path.dirname(os.path.abspath(__file__))
            cls._assets_path = os.path.join(gui_dir, 'assets')
        return cls._assets_path

    @classmethod
    def _load_card_image(cls, card: Card, is_back: bool = False):
        """
        Try to load a card image from assets/cards/

        Args:
            card: The card tuple (rank, suit)
            is_back: If True, load card back image

        Returns:
            PhotoImage object if found, None otherwise
        """
        if is_back:
            cache_key = 'card_back'
            filename = 'card_back.png'
        else:
            rank, suit = card
            cache_key = f"{rank}_{suit}"
            filename = f"{rank}_{suit}.png"

        # Check cache first
        if cache_key in cls._image_cache:
            return cls._image_cache[cache_key]

        # Try to load image
        assets_path = cls._get_assets_path()
        cards_path = os.path.join(assets_path, 'cards')
        image_path = os.path.join(cards_path, filename)

        if os.path.exists(image_path):
            try:
                # Load image using PhotoImage (supports PNG, GIF)
                img = tk.PhotoImage(file=image_path)
                cls._image_cache[cache_key] = img
                return img
            except Exception as e:
                print(f"Warning: Failed to load card image {filename}: {e}")
                return None

        return None

    def __init__(self, canvas, card: Card, x: int, y: int,
                 face_up: bool = True, clickable: bool = False,
                 show_value: bool = False, on_click_callback=None):
        self.canvas = canvas
        self.card = card
        self.x = x
        self.y = y
        self.face_up = face_up
        self.clickable = clickable
        self.show_value = show_value
        self.on_click_callback = on_click_callback
        self.selected = False
        self.card_id = None
        self.text_ids = []
        self.image_ref = None  # Keep reference to prevent garbage collection

        self.draw()

    def draw(self):
        """Draw the card on the canvas (tries to load image, falls back to programmatic drawing)"""
        # Clear previous drawing
        if self.card_id:
            self.canvas.delete(self.card_id)
            for text_id in self.text_ids:
                self.canvas.delete(text_id)
            self.text_ids = []

        y_offset = -10 if self.selected else 0

        # Try to load image first
        if self.face_up:
            self.image_ref = self._load_card_image(self.card, is_back=False)
        else:
            self.image_ref = self._load_card_image(self.card, is_back=True)

        # If image was loaded, use it
        if self.image_ref:
            self.card_id = self.canvas.create_image(
                self.x + self.CARD_WIDTH // 2,
                self.y + self.CARD_HEIGHT // 2 + y_offset,
                image=self.image_ref
            )

            # Still show value badge if requested (overlaid on image)
            if self.face_up and self.show_value:
                value, _ = calculate_hand_value([self.card])
                badge_x = self.x + self.CARD_WIDTH - 18
                badge_y = self.y + 12 + y_offset
                badge = self.canvas.create_oval(
                    badge_x - 12, badge_y - 10,
                    badge_x + 12, badge_y + 10,
                    fill='#333333', outline='white', width=1
                )
                self.text_ids.append(badge)
                value_text = self.canvas.create_text(
                    badge_x, badge_y,
                    text=str(value), font=('Arial', 9, 'bold'),
                    fill='white'
                )
                self.text_ids.append(value_text)

        # Otherwise, fall back to programmatic drawing
        else:
            self._draw_programmatic(y_offset)

        # Bind click event if clickable
        if self.clickable:
            self.canvas.tag_bind(self.card_id, '<Button-1>', self.on_click)
            for text_id in self.text_ids:
                self.canvas.tag_bind(text_id, '<Button-1>', self.on_click)

    def _draw_programmatic(self, y_offset: int):
        """Draw card using programmatic drawing (fallback when no image available)"""
        if self.face_up:
            # Draw card face
            fill_color = '#FFFFFF'
            outline_color = '#000000'

            self.card_id = self.canvas.create_rectangle(
                self.x, self.y + y_offset,
                        self.x + self.CARD_WIDTH, self.y + self.CARD_HEIGHT + y_offset,
                fill=fill_color, outline=outline_color, width=2
            )

            rank, suit = self.card
            suit_symbol = self.SUIT_SYMBOLS.get(suit, '?')
            suit_color = self.SUIT_COLORS.get(suit, '#000000')

            # Display rank (top-left and bottom-right)
            rank_text = self.canvas.create_text(
                self.x + 10, self.y + 15 + y_offset,
                text=rank, font=('Arial', 12, 'bold'),
                fill=suit_color
            )
            self.text_ids.append(rank_text)

            rank_text2 = self.canvas.create_text(
                self.x + self.CARD_WIDTH - 10, self.y + self.CARD_HEIGHT - 15 + y_offset,
                text=rank, font=('Arial', 12, 'bold'),
                fill=suit_color
            )
            self.text_ids.append(rank_text2)

            # Display suit symbol (center)
            suit_text = self.canvas.create_text(
                self.x + self.CARD_WIDTH // 2, self.y + self.CARD_HEIGHT // 2 + y_offset,
                text=suit_symbol, font=('Arial', 32),
                fill=suit_color
            )
            self.text_ids.append(suit_text)

            # If it's a Trionfi with a name, show it
            if suit == 'T':
                trionfi = get_trionfi_effect(self.card)
                if trionfi:
                    name_text = self.canvas.create_text(
                        self.x + self.CARD_WIDTH // 2, self.y + self.CARD_HEIGHT - 30 + y_offset,
                        text=trionfi.name, font=('Arial', 7),
                        fill=suit_color, width=self.CARD_WIDTH - 10
                    )
                    self.text_ids.append(name_text)

            # Show value badge if requested
            if self.show_value:
                value, _ = calculate_hand_value([self.card])
                # Draw badge background
                badge_x = self.x + self.CARD_WIDTH - 18
                badge_y = self.y + 12 + y_offset
                badge = self.canvas.create_oval(
                    badge_x - 12, badge_y - 10,
                    badge_x + 12, badge_y + 10,
                    fill='#333333', outline='white', width=1
                )
                self.text_ids.append(badge)
                # Draw value text
                value_text = self.canvas.create_text(
                    badge_x, badge_y,
                    text=str(value), font=('Arial', 9, 'bold'),
                    fill='white'
                )
                self.text_ids.append(value_text)

        else:
            # Draw card back
            self.card_id = self.canvas.create_rectangle(
                self.x, self.y + y_offset,
                        self.x + self.CARD_WIDTH, self.y + self.CARD_HEIGHT + y_offset,
                fill='#8B0000', outline='#000000', width=2
            )

            # Add pattern to card back
            pattern_text = self.canvas.create_text(
                self.x + self.CARD_WIDTH // 2, self.y + self.CARD_HEIGHT // 2 + y_offset,
                text='⛝', font=('Arial', 48),
                fill='#FFD700'
            )
            self.text_ids.append(pattern_text)

    def on_click(self, event):
        """Handle card click"""
        if self.on_click_callback:
            self.on_click_callback(self.card)
        else:
            self.selected = not self.selected
            self.draw()

    def move_to(self, x: int, y: int):
        """Move card to new position"""
        self.x = x
        self.y = y
        self.draw()


class ChipWidget:
    """Represents a visual chip for the pot display"""

    # Chip dimensions
    CHIP_SIZE = 30  # diameter

    # Chip denominations and colors
    CHIP_VALUES = [100, 25, 10, 5, 1]
    CHIP_COLORS = {
        1: '#FFFFFF',    # White
        5: '#FF0000',    # Red
        10: '#0000FF',   # Blue
        25: '#00AA00',   # Green
        100: '#000000'   # Black
    }
    CHIP_EDGE_COLORS = {
        1: '#CCCCCC',
        5: '#AA0000',
        10: '#000088',
        25: '#008800',
        100: '#444444'
    }

    # Image cache
    _chip_image_cache = {}

    @classmethod
    def _load_chip_image(cls, value: int):
        """
        Try to load a chip image from assets/chips/

        Args:
            value: The chip denomination (1, 5, 10, 25, 100)

        Returns:
            PhotoImage object if found, None otherwise
        """
        cache_key = f"chip_{value}"

        # Check cache first
        if cache_key in cls._chip_image_cache:
            return cls._chip_image_cache[cache_key]

        # Try to load image
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(gui_dir, 'assets')
        chips_path = os.path.join(assets_path, 'chips')
        image_path = os.path.join(chips_path, f"chip_{value}.png")

        if os.path.exists(image_path):
            try:
                img = tk.PhotoImage(file=image_path)
                cls._chip_image_cache[cache_key] = img
                return img
            except Exception as e:
                print(f"Warning: Failed to load chip image chip_{value}.png: {e}")
                return None

        return None

    def __init__(self, canvas, value: int, x: int, y: int, count: int = 1):
        self.canvas = canvas
        self.value = value
        self.x = x
        self.y = y
        self.count = count  # Number of chips in this stack
        self.canvas_ids = []
        self.image_ref = None

    def draw(self):
        """Draw the chip stack on the canvas"""
        # Clear previous drawing
        for cid in self.canvas_ids:
            self.canvas.delete(cid)
        self.canvas_ids = []

        # Try to load image first
        self.image_ref = self._load_chip_image(self.value)

        if self.image_ref:
            # Draw stacked chips using images
            for i in range(min(self.count, 5)):  # Max 5 visual chips in a stack
                offset = i * 3
                cid = self.canvas.create_image(
                    self.x + offset,
                    self.y + offset,
                    image=self.image_ref
                )
                self.canvas_ids.append(cid)
        else:
            # Programmatic drawing fallback
            self._draw_programmatic()

        # Add count label if more than 5 chips
        if self.count > 5:
            text_bg = self.canvas.create_oval(
                self.x + self.CHIP_SIZE - 5, self.y - 8,
                self.x + self.CHIP_SIZE + 10, self.y + 7,
                fill='#FFFF00', outline='#000000', width=1
            )
            self.canvas_ids.append(text_bg)
            text_id = self.canvas.create_text(
                self.x + self.CHIP_SIZE + 2, self.y,
                text=str(self.count), font=('Arial', 9, 'bold'),
                fill='#000000'
            )
            self.canvas_ids.append(text_id)

    def _draw_programmatic(self):
        """Draw chip using programmatic drawing"""
        color = self.CHIP_COLORS.get(self.value, '#888888')
        edge_color = self.CHIP_EDGE_COLORS.get(self.value, '#444444')

        # Draw stacked chips (max 5 visual)
        for i in range(min(self.count, 5)):
            offset = i * 3

            # Outer circle (edge)
            outer = self.canvas.create_oval(
                self.x - self.CHIP_SIZE // 2 + offset,
                self.y - self.CHIP_SIZE // 2 + offset,
                self.x + self.CHIP_SIZE // 2 + offset,
                self.y + self.CHIP_SIZE // 2 + offset,
                fill=edge_color, outline=edge_color, width=2
            )
            self.canvas_ids.append(outer)

            # Inner circle (face)
            inner = self.canvas.create_oval(
                self.x - self.CHIP_SIZE // 2 + 3 + offset,
                self.y - self.CHIP_SIZE // 2 + 3 + offset,
                self.x + self.CHIP_SIZE // 2 - 3 + offset,
                self.y + self.CHIP_SIZE // 2 - 3 + offset,
                fill=color, outline=edge_color, width=2
            )
            self.canvas_ids.append(inner)

        # Value text on top chip
        top_offset = min(self.count - 1, 4) * 3
        text_id = self.canvas.create_text(
            self.x + top_offset, self.y + top_offset,
            text=str(self.value), font=('Arial', 10, 'bold'),
            fill='#FFFFFF' if self.value == 100 else '#000000'
        )
        self.canvas_ids.append(text_id)

    def clear(self):
        """Remove chip from canvas"""
        for cid in self.canvas_ids:
            self.canvas.delete(cid)
        self.canvas_ids = []


class PotDisplay:
    """Manages the visual display of the pot with chip stacks"""

    def __init__(self, canvas, x: int, y: int):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.chip_widgets = []
        self.label_id = None

    def update(self, pot_value: int):
        """Update the pot display to show current value"""
        # Clear existing chips
        for chip in self.chip_widgets:
            chip.clear()
        self.chip_widgets = []

        if self.label_id:
            self.canvas.delete(self.label_id)

        if pot_value == 0:
            # Show "Pot: 0" text
            self.label_id = self.canvas.create_text(
                self.x, self.y,
                text="Pot: 0", font=('Arial', 14, 'bold'),
                fill='#FFFF00'
            )
            return

        # Calculate chip breakdown
        remaining = pot_value
        chip_counts = {}

        for value in ChipWidget.CHIP_VALUES:
            count = remaining // value
            if count > 0:
                chip_counts[value] = count
                remaining -= count * value

        # Position chips in a nice layout
        chip_x = self.x - 40
        for value in ChipWidget.CHIP_VALUES:
            if value in chip_counts:
                chip = ChipWidget(self.canvas, value, chip_x, self.y, chip_counts[value])
                chip.draw()
                self.chip_widgets.append(chip)
                chip_x += 45

        # Add pot total label
        self.label_id = self.canvas.create_text(
            self.x, self.y - 35,
            text=f"Pot: {pot_value}", font=('Arial', 12, 'bold'),
            fill='#FFFF00'
        )

    def clear(self):
        """Clear the entire pot display"""
        for chip in self.chip_widgets:
            chip.clear()
        self.chip_widgets = []
        if self.label_id:
            self.canvas.delete(self.label_id)
            self.label_id = None


class SabaccGUI:
    """Main GUI window for Sabacc game"""

    def __init__(self, root):
        self.root = root
        self.root.title("Sabacc con i Tarocchi")
        self.root.geometry("1000x750")
        self.root.resizable(False, False)

        # Game state
        self.game: Optional[GameState] = None
        self.card_widgets: List[CardWidget] = []
        self.pot_display: Optional[PotDisplay] = None
        self.current_player_action = {}  # Accumulate actions during turn
        self.waiting_for_input = False
        self.input_type = None  # 'draw_source', 'discard_index', etc.
        self.current_phase = 'flop'  # 'flop', 'turn', 'river', 'showdown'

        # Setup UI
        self.setup_menu()
        self.setup_canvas()
        self.setup_info_panel()
        self.setup_buttons()
        self.setup_log()

        # Start new game
        self.new_game()

    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Game menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="New Game", command=self.new_game)
        game_menu.add_separator()
        game_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Rules", command=self.show_rules)
        help_menu.add_command(label="About", command=self.show_about)

    def setup_canvas(self):
        """Create main canvas for card display"""
        self.canvas = tk.Canvas(
            self.root,
            width=1000,
            height=500,
            bg='#008000'  # Green felt
        )
        self.canvas.pack(pady=5)

    def setup_info_panel(self):
        """Create info panel showing game state"""
        info_frame = tk.Frame(self.root, relief=tk.SUNKEN, borderwidth=2)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        # Left side - Player info
        left_frame = tk.Frame(info_frame)
        left_frame.pack(side=tk.LEFT, padx=10)

        self.credits_label = tk.Label(
            left_frame,
            text="Credits: 0",
            font=('Arial', 12, 'bold')
        )
        self.credits_label.pack(side=tk.LEFT, padx=10)

        self.hand_value_label = tk.Label(
            left_frame,
            text="Hand Value: 0",
            font=('Arial', 12)
        )
        self.hand_value_label.pack(side=tk.LEFT, padx=10)

        # Center - Turn indicator
        center_frame = tk.Frame(info_frame)
        center_frame.pack(side=tk.LEFT, expand=True)

        self.turn_indicator = tk.Label(
            center_frame,
            text="Your Turn",
            font=('Arial', 12, 'bold'),
            bg='#90EE90',  # Light green
            fg='black',
            padx=15,
            pady=5,
            relief=tk.RAISED,
            borderwidth=2
        )
        self.turn_indicator.pack()

        # Right side - Pot info
        right_frame = tk.Frame(info_frame)
        right_frame.pack(side=tk.RIGHT, padx=10)

        self.pot_label = tk.Label(
            right_frame,
            text="Pot: 0",
            font=('Arial', 12, 'bold')
        )
        self.pot_label.pack(side=tk.LEFT, padx=10)

        self.current_bet_label = tk.Label(
            right_frame,
            text="Current Bet: 0",
            font=('Arial', 12)
        )
        self.current_bet_label.pack(side=tk.LEFT, padx=10)

    def setup_buttons(self):
        """Create action buttons"""
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        self.fold_btn = tk.Button(
            button_frame,
            text="Fold",
            width=10,
            command=self.on_fold,
            state=tk.DISABLED
        )
        self.fold_btn.pack(side=tk.LEFT, padx=5)

        self.call_btn = tk.Button(
            button_frame,
            text="Call",
            width=10,
            command=self.on_call,
            state=tk.DISABLED
        )
        self.call_btn.pack(side=tk.LEFT, padx=5)

        self.raise_btn = tk.Button(
            button_frame,
            text="Raise",
            width=10,
            command=self.on_raise,
            state=tk.DISABLED
        )
        self.raise_btn.pack(side=tk.LEFT, padx=5)

        self.draw_btn = tk.Button(
            button_frame,
            text="Draw Card",
            width=10,
            command=self.on_draw,
            state=tk.DISABLED
        )
        self.draw_btn.pack(side=tk.LEFT, padx=5)

        self.discard_btn = tk.Button(
            button_frame,
            text="Discard",
            width=10,
            command=self.on_discard,
            state=tk.DISABLED
        )
        self.discard_btn.pack(side=tk.LEFT, padx=5)

        self.end_turn_btn = tk.Button(
            button_frame,
            text="End Turn",
            width=10,
            command=self.end_player_turn,
            state=tk.DISABLED
        )
        self.end_turn_btn.pack(side=tk.LEFT, padx=5)

        self.special_btn = tk.Button(
            button_frame,
            text="Play Special",
            width=12,
            command=self.on_play_special,
            state=tk.DISABLED
        )
        self.special_btn.pack(side=tk.LEFT, padx=5)

    def setup_log(self):
        """Create game log"""
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_label = tk.Label(log_frame, text="Game Log:", anchor=tk.W)
        log_label.pack(fill=tk.X)

        # Scrollbar
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget for log
        self.log_text = tk.Text(
            log_frame,
            height=8,
            state=tk.DISABLED,
            yscrollcommand=scrollbar.set
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def update_buttons(self):
        """Enable/disable buttons based on current game state"""
        if not self.game:
            return

        player = self.game.players[0]

        # Check if player is in hermit mode - disable all actions
        if getattr(player, 'is_hermit', False):
            self.fold_btn.config(state=tk.DISABLED)
            self.call_btn.config(state=tk.DISABLED)
            self.raise_btn.config(state=tk.DISABLED)
            self.draw_btn.config(state=tk.DISABLED)
            self.discard_btn.config(state=tk.DISABLED)
            self.end_turn_btn.config(state=tk.DISABLED)
            self.special_btn.config(state=tk.DISABLED)
            self.set_turn_player()  # Shows "Hermit Mode"
            return

        # Check if it's player's turn and they haven't acted yet
        is_players_turn = not player.has_folded and not player.has_acted

        if is_players_turn and not self.waiting_for_input:
            # Betting buttons
            self.fold_btn.config(state=tk.NORMAL)

            amount_to_call = self.game.current_bet - player.current_bet
            if amount_to_call > 0:
                self.call_btn.config(text=f"Call {amount_to_call}", state=tk.NORMAL)
            else:
                self.call_btn.config(text="Check", state=tk.NORMAL)

            if player.credits > self.game.current_bet - player.current_bet:
                self.raise_btn.config(state=tk.NORMAL)
            else:
                self.raise_btn.config(state=tk.DISABLED)

            # Draw button (only if haven't drawn yet)
            if not player.has_drawn and 'bet_action' in self.current_player_action:
                self.draw_btn.config(state=tk.NORMAL)
            else:
                self.draw_btn.config(state=tk.DISABLED)

            # Discard button (only if have cards and have drawn or bet)
            if len(player.hand) > 0 and 'bet_action' in self.current_player_action:
                self.discard_btn.config(state=tk.NORMAL)
            else:
                self.discard_btn.config(state=tk.DISABLED)

            # End Turn button (only if have placed a bet)
            if 'bet_action' in self.current_player_action:
                self.end_turn_btn.config(state=tk.NORMAL)
            else:
                self.end_turn_btn.config(state=tk.DISABLED)

            # Special card button
            playable = get_playable_trionfi(player)
            if playable and 'bet_action' in self.current_player_action:
                self.special_btn.config(state=tk.NORMAL)
            else:
                self.special_btn.config(state=tk.DISABLED)

            # Update turn indicator
            self.set_turn_player()
        else:
            # Not player's turn - disable all buttons
            self.fold_btn.config(state=tk.DISABLED)
            self.call_btn.config(state=tk.DISABLED)
            self.raise_btn.config(state=tk.DISABLED)
            self.draw_btn.config(state=tk.DISABLED)
            self.discard_btn.config(state=tk.DISABLED)
            self.end_turn_btn.config(state=tk.DISABLED)
            self.special_btn.config(state=tk.DISABLED)

    def log(self, message: str):
        """Add message to game log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def new_game(self):
        """Start a new game"""
        # Get player name
        player_name = simpledialog.askstring(
            "New Game",
            "Enter your name:",
            initialvalue="Player"
        )
        if not player_name:
            player_name = "Player"

        # Get number of opponents
        num_opponents = simpledialog.askinteger(
            "New Game",
            "Number of opponents (1-3):",
            initialvalue=3,
            minvalue=1,
            maxvalue=3
        )
        if not num_opponents:
            num_opponents = 3

        # Create game
        opponent_names = get_random_opponent_names(num_opponents)
        self.game = GameState([player_name] + opponent_names, starting_credits=500, min_bet=2)

        self.log(f"=== NEW GAME ===")
        self.log(f"Players: {', '.join([p.name for p in self.game.players])}")
        self.log(f"Starting credits: 500")
        self.log(f"Minimum bet: 2")

        # Start first hand
        self.start_new_hand()

    def start_new_hand(self):
        """Start a new hand"""
        self.game.start_new_hand()
        self.current_phase = 'flop'
        self.log(f"\n=== HAND #{self.game.hand_number} ===")
        self.log(f"Dealer: {self.game.players[self.game.dealer_index].name}")

        # Collect blinds
        self.game.collect_blinds()
        self.log(f"Blinds collected. Pot: {self.game.pot}")

        # Deal initial cards
        self.game.deal_initial_cards()
        self.log(f"Flop: {self.game.community_cards}")

        # Reset action
        self.current_player_action = {}

        # Update display
        self.update_display()

        # Enable buttons for first player
        self.update_buttons()

        self.log("\nYour turn! Place your bet.")

    def update_display(self):
        """Update the entire display"""
        # Clear canvas
        self.canvas.delete("all")
        self.card_widgets = []

        if not self.game:
            return

        # Draw opponent hands (card backs)
        opponent_y = 20
        for i, player in enumerate(self.game.players[1:], 1):
            if player.has_folded:
                continue

            opponent_x = 50 + (i - 1) * 250

            # Player name and info
            self.canvas.create_text(
                opponent_x, opponent_y,
                text=f"{player.name}\nCredits: {player.credits}",
                anchor=tk.NW,
                font=('Arial', 10, 'bold')
            )

            # Draw card backs
            for j in range(len(player.hand)):
                card_x = opponent_x + j * 20
                card_y = opponent_y + 30

                # Show face up if hands_face_up flag is set
                face_up = getattr(self.game, 'hands_face_up', False)

                card_widget = CardWidget(
                    self.canvas,
                    player.hand[j] if face_up else ('?', '?'),
                    card_x, card_y,
                    face_up=face_up,
                    clickable=False
                )
                self.card_widgets.append(card_widget)

        # Draw discard pile (left side)
        discard_x = 50
        discard_y = 200

        self.canvas.create_text(
            discard_x + 35, discard_y - 30,
            text="Discard Pile",
            font=('Arial', 12, 'bold'),
            fill='white'
        )

        if self.game.discard_pile:
            # Show top card of discard pile
            top_card = self.game.discard_pile[-1]
            discard_widget = CardWidget(
                self.canvas,
                top_card,
                discard_x, discard_y,
                face_up=True,
                clickable=True,
                on_click_callback=self.show_discard_pile
            )
            self.card_widgets.append(discard_widget)

            # Show card count badge
            count = len(self.game.discard_pile)
            if count > 1:
                self.canvas.create_oval(
                    discard_x + 50, discard_y + 70,
                    discard_x + 75, discard_y + 95,
                    fill='#CC0000', outline='white', width=2
                )
                self.canvas.create_text(
                    discard_x + 62, discard_y + 82,
                    text=str(count), font=('Arial', 11, 'bold'),
                    fill='white'
                )
        else:
            # Empty pile placeholder
            self.canvas.create_rectangle(
                discard_x, discard_y,
                discard_x + CardWidget.CARD_WIDTH, discard_y + CardWidget.CARD_HEIGHT,
                fill='#006400', outline='white', width=2, dash=(4, 4)
            )
            self.canvas.create_text(
                discard_x + CardWidget.CARD_WIDTH // 2, discard_y + CardWidget.CARD_HEIGHT // 2,
                text="Empty", font=('Arial', 10),
                fill='white'
            )

        # Draw draw pile indicator (next to discard)
        draw_pile_x = 140
        draw_pile_y = 200

        self.canvas.create_text(
            draw_pile_x + 35, draw_pile_y - 30,
            text="Draw Pile",
            font=('Arial', 12, 'bold'),
            fill='white'
        )

        # Draw a face-down card to represent draw pile
        if self.game.draw_pile.cards:
            draw_pile_widget = CardWidget(
                self.canvas,
                ('?', '?'),
                draw_pile_x, draw_pile_y,
                face_up=False,
                clickable=False
            )
            self.card_widgets.append(draw_pile_widget)

            # Show remaining count
            remaining = len(self.game.draw_pile.cards)
            self.canvas.create_oval(
                draw_pile_x + 50, draw_pile_y + 70,
                draw_pile_x + 75, draw_pile_y + 95,
                fill='#0066CC', outline='white', width=2
            )
            self.canvas.create_text(
                draw_pile_x + 62, draw_pile_y + 82,
                text=str(remaining), font=('Arial', 11, 'bold'),
                fill='white'
            )

        # Draw community cards
        community_y = 200
        community_x_start = 400

        self.canvas.create_text(
            community_x_start, community_y - 30,
            text="Community Cards",
            font=('Arial', 12, 'bold'),
            fill='white'
        )

        for i, card in enumerate(self.game.community_cards):
            card_x = community_x_start + i * 80
            card_widget = CardWidget(
                self.canvas,
                card,
                card_x, community_y,
                face_up=True,
                clickable=False
            )
            self.card_widgets.append(card_widget)

        # Draw pot display (center of table, below community cards)
        pot_x = 500
        pot_y = 320
        if not self.pot_display:
            self.pot_display = PotDisplay(self.canvas, pot_x, pot_y)
        else:
            # Reassign canvas in case it was cleared
            self.pot_display.canvas = self.canvas
            self.pot_display.x = pot_x
            self.pot_display.y = pot_y
        self.pot_display.update(self.game.pot)

        # Draw player's hand (at bottom)
        player = self.game.players[0]
        player_y = 380
        player_x_start = 300

        for i, card in enumerate(player.hand):
            card_x = player_x_start + i * 80
            card_widget = CardWidget(
                self.canvas,
                card,
                card_x, player_y,
                face_up=True,
                clickable=True
            )
            self.card_widgets.append(card_widget)

        # Update info labels
        self.update_info_labels()

    def update_info_labels(self):
        """Update the info panel labels"""
        if not self.game:
            return

        player = self.game.players[0]
        value, busted = calculate_hand_value(player.hand)
        status = " (BUSTED)" if busted else ""

        self.credits_label.config(text=f"Credits: {player.credits}")
        self.hand_value_label.config(text=f"Hand Value: {value}{status}")
        self.pot_label.config(text=f"Pot: {self.game.pot}")
        self.current_bet_label.config(text=f"Current Bet: {self.game.current_bet}")

    def update_turn_indicator(self, text: str, color: str):
        """Update the turn indicator with text and background color"""
        self.turn_indicator.config(text=text, bg=color)

    def set_turn_player(self):
        """Set indicator to show it's the player's turn"""
        player = self.game.players[0]
        if getattr(player, 'is_hermit', False):
            self.update_turn_indicator("Hermit Mode", '#DDA0DD')  # Plum
        elif player.has_folded:
            self.update_turn_indicator("Folded", '#D3D3D3')  # Light gray
        else:
            self.update_turn_indicator("Your Turn", '#90EE90')  # Light green

    def set_turn_ai(self, ai_name: str = "AI"):
        """Set indicator to show AI is thinking"""
        self.update_turn_indicator(f"{ai_name} thinking...", '#FFD700')  # Gold

    def set_turn_waiting(self, text: str = "Waiting..."):
        """Set indicator to waiting state"""
        self.update_turn_indicator(text, '#D3D3D3')  # Light gray

    def show_discard_pile(self, clicked_card=None):
        """Show a dialog with all cards in the discard pile"""
        if not self.game.discard_pile:
            messagebox.showinfo("Discard Pile", "The discard pile is empty.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Discard Pile")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Discard Pile Contents",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        tk.Label(dialog, text="(Bottom to Top - newest cards at bottom)",
                 font=('Arial', 9, 'italic')).pack()

        # Create scrollable frame
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, width=60, height=15,
                            yscrollcommand=scrollbar.set,
                            font=('Courier', 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Add cards to listbox
        for i, card in enumerate(self.game.discard_pile):
            rank, suit = card
            suit_names = {'W': 'Wands', 'C': 'Cups', 'S': 'Swords', 'D': 'Disks', 'T': 'Trionfi'}
            suit_name = suit_names.get(suit, suit)
            value, _ = calculate_hand_value([card])

            if suit == 'T':
                trionfi = get_trionfi_effect(card)
                name = trionfi.name if trionfi else f"Trionfo {rank}"
                listbox.insert(tk.END, f"{i+1:3}. {name:<20} (value: {value:>3})")
            else:
                listbox.insert(tk.END, f"{i+1:3}. {rank:>2} of {suit_name:<8} (value: {value:>3})")

        # Total value
        total_value, _ = calculate_hand_value(self.game.discard_pile)
        tk.Label(dialog, text=f"Total cards: {len(self.game.discard_pile)}",
                 font=('Arial', 10)).pack(pady=5)

        tk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(pady=10)

    # Button handlers (stubs for now)
    def on_fold(self):
        """Handle fold button"""
        self.current_player_action['bet_action'] = 'fold'
        self.log("You fold.")
        self.end_player_turn()

    def on_call(self):
        """Handle call/check button"""
        self.current_player_action['bet_action'] = 'call'
        amount_to_call = self.game.current_bet - self.game.players[0].current_bet
        if amount_to_call > 0:
            self.log(f"You call {amount_to_call}.")
        else:
            self.log("You check.")
        self.update_buttons()
        self.update_display()

    def on_raise(self):
        """Handle raise button"""
        player = self.game.players[0]
        amount_to_call = self.game.current_bet - player.current_bet
        max_raise = player.credits - amount_to_call

        raise_amount = simpledialog.askinteger(
            "Raise",
            f"Raise amount (min {self.game.min_bet}, max {max_raise}):",
            minvalue=self.game.min_bet,
            maxvalue=max_raise
        )

        if raise_amount:
            self.current_player_action['bet_action'] = 'raise'
            self.current_player_action['raise_amount'] = raise_amount
            self.log(f"You raise {raise_amount}.")
            self.update_buttons()
            self.update_display()

    def on_draw(self):
        """Handle draw button"""
        # Ask player where to draw from
        draw_dialog = tk.Toplevel(self.root)
        draw_dialog.title("Draw Card")
        draw_dialog.geometry("300x200")
        draw_dialog.transient(self.root)
        draw_dialog.grab_set()

        tk.Label(draw_dialog, text="Draw from:", font=('Arial', 12, 'bold')).pack(pady=10)

        def draw_from_pile():
            self.current_player_action['draw_action'] = 'draw_pile'
            self.log("You draw from the draw pile.")
            draw_dialog.destroy()
            self.process_draw()

        def draw_from_discard():
            if not self.game.discard_pile:
                messagebox.showwarning("No Cards", "Discard pile is empty!")
                return
            draw_dialog.destroy()
            self.choose_discard_pile_card()

        def swap_community():
            draw_dialog.destroy()
            self.choose_community_swap()

        def skip():
            draw_dialog.destroy()
            self.update_buttons()

        tk.Button(draw_dialog, text="Draw Pile", width=20, command=draw_from_pile).pack(pady=5)

        if self.game.discard_pile:
            tk.Button(draw_dialog, text="Discard Pile", width=20, command=draw_from_discard).pack(pady=5)

        tk.Button(draw_dialog, text="Swap with Community", width=20, command=swap_community).pack(pady=5)
        tk.Button(draw_dialog, text="Skip", width=20, command=skip).pack(pady=5)

    def choose_discard_pile_card(self):
        """Let player choose which card from discard pile"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose Card from Discard Pile")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Choose a card (you'll take it and all cards above it):",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        listbox = tk.Listbox(dialog, width=40, height=10)
        listbox.pack(pady=5)

        for i, card in enumerate(self.game.discard_pile):
            listbox.insert(tk.END, f"{i}: {card}")

        def confirm():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                self.current_player_action['draw_action'] = 'discard_pile'
                self.current_player_action['draw_index'] = idx
                cards = self.game.discard_pile[idx:]
                self.log(f"You draw from discard pile: {cards}")
                dialog.destroy()
                self.process_draw()
            else:
                messagebox.showwarning("Selection Required", "Please select a card.")

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=10)

    def choose_community_swap(self):
        """Let player choose cards to swap with community"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Swap with Community")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()

        player = self.game.players[0]

        selected_hand_idx = tk.IntVar(value=-1)
        selected_comm_idx = tk.IntVar(value=-1)

        tk.Label(dialog, text="Step 1: Choose a card from your hand:",
                 font=('Arial', 10, 'bold')).pack(pady=5)

        hand_frame = tk.Frame(dialog)
        hand_frame.pack(pady=5)

        for i, card in enumerate(player.hand):
            rb = tk.Radiobutton(
                hand_frame,
                text=f"{card}",
                variable=selected_hand_idx,
                value=i
            )
            rb.pack(anchor=tk.W)

        tk.Label(dialog, text="Step 2: Choose a community card to take:",
                 font=('Arial', 10, 'bold')).pack(pady=5)

        comm_frame = tk.Frame(dialog)
        comm_frame.pack(pady=5)

        for i, card in enumerate(self.game.community_cards):
            rb = tk.Radiobutton(
                comm_frame,
                text=f"{card}",
                variable=selected_comm_idx,
                value=i
            )
            rb.pack(anchor=tk.W)

        def confirm():
            hand_idx = selected_hand_idx.get()
            comm_idx = selected_comm_idx.get()

            if hand_idx >= 0 and comm_idx >= 0:
                self.current_player_action['draw_action'] = 'community'
                self.current_player_action['hand_card_index'] = hand_idx
                self.current_player_action['community_card_index'] = comm_idx

                given = player.hand[hand_idx]
                taken = self.game.community_cards[comm_idx]
                self.log(f"You swap {given} for {taken}")

                dialog.destroy()
                self.process_draw()
            else:
                messagebox.showwarning("Selection Required", "Please select both cards.")

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=10)

    def process_draw(self):
        """Process the draw action and update display"""
        player = self.game.players[0]

        # Execute the draw based on current_player_action
        draw_action = self.current_player_action.get('draw_action')

        if draw_action == 'draw_pile':
            self.game.draw_from_draw_pile(player)
        elif draw_action == 'discard_pile':
            idx = self.current_player_action.get('draw_index', 0)
            self.game.draw_from_discard_pile(player, idx)
        elif draw_action == 'community':
            hand_idx = self.current_player_action['hand_card_index']
            comm_idx = self.current_player_action['community_card_index']
            self.game.swap_with_community(player, hand_idx, comm_idx)

        # Update display to show new cards
        self.update_display()
        self.update_buttons()

    def on_discard(self):
        """Handle discard button"""
        player = self.game.players[0]

        if not player.hand:
            messagebox.showwarning("No Cards", "You have no cards to discard!")
            return

        # Create dialog to choose card
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose Card to Discard")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Choose a card to discard:",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        listbox = tk.Listbox(dialog, width=40, height=15)
        listbox.pack(pady=5)

        for i, card in enumerate(player.hand):
            value, _ = calculate_hand_value([card])
            listbox.insert(tk.END, f"{i}: {card} (value: {value})")

        def confirm():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                self.current_player_action['discard_index'] = idx
                card = player.hand[idx]
                self.log(f"You will discard {card}")
                dialog.destroy()
                self.update_buttons()
            else:
                messagebox.showwarning("Selection Required", "Please select a card.")

        def skip():
            self.log("You skip discarding.")
            dialog.destroy()
            self.update_buttons()

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=5)
        tk.Button(dialog, text="Skip", command=skip).pack(pady=5)

    def on_play_special(self):
        """Handle play special card button"""
        player = self.game.players[0]
        playable = get_playable_trionfi(player)

        if not playable:
            messagebox.showinfo("No Special Cards", "You have no special cards to play.")
            return

        # Create dialog to choose special card
        dialog = tk.Toplevel(self.root)
        dialog.title("Play Special Card")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Choose a special card to play:",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        listbox = tk.Listbox(dialog, width=50, height=10)
        listbox.pack(pady=5)

        for i, (card, trionfi) in enumerate(playable):
            listbox.insert(tk.END, f"{trionfi.name} - {trionfi.description}")

        def confirm():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                card, trionfi = playable[idx]
                dialog.destroy()

                # Handle specific trionfi with GUI dialogs
                if trionfi.number == 4:  # The Emperor
                    self.play_emperor_effect(card)
                elif trionfi.number == 5:  # The Hierophant
                    self.play_hierophant_effect(card)
                elif trionfi.number == 9:  # The Hermit
                    self.play_hermit_effect(card)
                elif trionfi.number == 10:  # Wheel of Fortune
                    self.play_wheel_of_fortune_effect(card)
                elif trionfi.number == 18:  # The Moon
                    self.play_moon_effect(card)
                elif trionfi.number == 19:  # The Sun
                    self.play_sun_effect(card)
                elif trionfi.number == 20:  # The Last Judgment
                    self.play_judgment_effect(card)
                elif trionfi.number == 21:  # The Universe
                    self.play_universe_effect(card)
                else:
                    # For other trionfi, use the default behavior
                    self.current_player_action['play_trionfi'] = card
                    self.log(f"You play {trionfi.name}")
                    self.update_buttons()
            else:
                messagebox.showwarning("Selection Required", "Please select a card.")

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=10)

    def play_emperor_effect(self, card):
        """GUI handler for The Emperor effect"""
        player = self.game.players[0]

        # Get valid targets
        targets = [p for p in self.game.players
                   if p != player and not p.has_folded and not getattr(p, 'is_hermit', False)]

        if not targets:
            messagebox.showinfo("No Targets", "No valid targets for The Emperor's effect.")
            return

        # Create target selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("The Emperor - Choose Target")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Choose a player to target:",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        listbox = tk.Listbox(dialog, width=30, height=6)
        listbox.pack(pady=5)

        for i, p in enumerate(targets):
            listbox.insert(tk.END, f"{p.name} ({p.credits} credits)")

        def confirm_target():
            selection = listbox.curselection()
            if selection:
                target = targets[selection[0]]
                dialog.destroy()
                self.emperor_target_response(player, target, card)
            else:
                messagebox.showwarning("Selection Required", "Please select a target.")

        tk.Button(dialog, text="Target", command=confirm_target).pack(pady=10)

    def emperor_target_response(self, attacker, target, card):
        """Handle the target's response to The Emperor"""
        self.log(f"\n👑 {attacker.name} plays The Emperor targeting {target.name}!")

        # Remove the card from attacker's hand
        if card in attacker.hand:
            attacker.hand.remove(card)
            self.game.removed_pile.append(card)

        if target.is_human:
            # Human target - show choice dialog
            self.emperor_human_response(target)
        else:
            # AI target - auto-decide
            self.emperor_ai_response(target)

    def emperor_human_response(self, target):
        """Show dialog for human player to respond to Emperor"""
        dialog = tk.Toplevel(self.root)
        dialog.title("The Emperor - Your Response")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"You have been targeted by The Emperor!",
                 font=('Arial', 10, 'bold')).pack(pady=5)
        tk.Label(dialog, text="Choose your response:").pack(pady=5)

        def ante_up():
            if target.credits >= self.game.min_bet:
                target.credits -= self.game.min_bet
                self.game.pot += self.game.min_bet
                self.log(f"{target.name} antes up {self.game.min_bet} credits.")
            else:
                self.log(f"{target.name} doesn't have enough credits and must fold!")
                self.game.player_fold(target)
            dialog.destroy()
            self.update_display()

        def discard_two():
            dialog.destroy()
            if len(target.hand) >= 2:
                self.emperor_discard_two(target)
            else:
                self.log(f"{target.name} doesn't have 2 cards and must fold!")
                self.game.player_fold(target)
                self.update_display()

        def fold():
            self.game.player_fold(target)
            self.log(f"{target.name} folds.")
            dialog.destroy()
            self.update_display()

        tk.Button(dialog, text=f"Ante up {self.game.min_bet} credits",
                  width=25, command=ante_up).pack(pady=5)
        tk.Button(dialog, text="Discard 2 cards",
                  width=25, command=discard_two).pack(pady=5)
        tk.Button(dialog, text="Fold",
                  width=25, command=fold).pack(pady=5)

    def emperor_discard_two(self, target):
        """Dialog for target to discard 2 cards"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Discard 2 Cards")
        dialog.geometry("350x350")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Select 2 cards to discard:",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        # Use checkbuttons for multi-select
        selected = []
        check_vars = []

        for i, card in enumerate(target.hand):
            var = tk.BooleanVar()
            check_vars.append(var)
            cb = tk.Checkbutton(dialog, text=f"{card}", variable=var)
            cb.pack(anchor=tk.W, padx=20)

        def confirm():
            selected_indices = [i for i, var in enumerate(check_vars) if var.get()]
            if len(selected_indices) == 2:
                # Discard the selected cards
                cards_to_discard = [target.hand[i] for i in selected_indices]
                for c in cards_to_discard:
                    target.hand.remove(c)
                    self.game.discard_pile.append(c)
                self.log(f"{target.name} discards {cards_to_discard}")
                dialog.destroy()
                self.update_display()
            else:
                messagebox.showwarning("Selection Required", "Please select exactly 2 cards.")

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=10)

    def emperor_ai_response(self, target):
        """AI response to The Emperor"""
        value, busted = calculate_hand_value(target.hand)

        if busted or abs(value) < 10:
            self.game.player_fold(target)
            self.log(f"{target.name} folds.")
        elif target.credits >= self.game.min_bet and abs(value) >= 18:
            target.credits -= self.game.min_bet
            self.game.pot += self.game.min_bet
            self.log(f"{target.name} antes up {self.game.min_bet} credits.")
        else:
            if len(target.hand) >= 2:
                import random
                to_discard = random.sample(target.hand, 2)
                for c in to_discard:
                    target.hand.remove(c)
                    self.game.discard_pile.append(c)
                self.log(f"{target.name} discards 2 cards.")
            else:
                self.game.player_fold(target)
                self.log(f"{target.name} folds.")

        self.update_display()

    def play_hierophant_effect(self, card):
        """GUI handler for The Hierophant effect"""
        player = self.game.players[0]

        self.log(f"\n⛪ {player.name} plays The Hierophant!")
        self.log("All players must reveal their hand values or fold!")

        # Remove the card from hand
        if card in player.hand:
            player.hand.remove(card)
            self.game.removed_pile.append(card)

        # Process all other players
        revealed_info = []
        for p in self.game.players:
            if p == player or p.has_folded or getattr(p, 'is_hermit', False):
                continue

            # AI players auto-decide based on hand strength
            value, busted = calculate_hand_value(p.hand)

            if busted or abs(value) < 8:
                self.game.player_fold(p)
                self.log(f"{p.name} folds rather than reveal.")
                revealed_info.append(f"{p.name}: Folded")
            else:
                status = "[BUSTED]" if busted else "[OK]"
                self.log(f"{p.name} reveals hand value: {value} {status}")
                revealed_info.append(f"{p.name}: {value} {status}")

        # Update display
        self.update_display()
        self.update_buttons()

        # Show summary dialog
        if revealed_info:
            messagebox.showinfo("The Hierophant",
                "Hand values revealed:\n\n" + "\n".join(revealed_info))
        else:
            messagebox.showinfo("The Hierophant",
                "No players were affected.")

    def play_hermit_effect(self, card):
        """GUI handler for The Hermit effect"""
        player = self.game.players[0]

        self.log(f"\n🧙 {player.name} plays The Hermit!")
        self.log(f"{player.name} withdraws from betting and advances to showdown.")

        # Mark player as hermit - they're still in but can't be affected
        player.is_hermit = True

        # The Hermit stays in hand (stays_in_hand=True in registry)
        # So we don't remove the card

        # Disable all actions and update display
        self.update_display()
        self.update_buttons()

        messagebox.showinfo("The Hermit",
            "You have withdrawn from betting.\n"
            "You will automatically advance to showdown.\n"
            "You are immune from special effects.")

    def play_wheel_of_fortune_effect(self, card):
        """GUI handler for Wheel of Fortune effect"""
        player = self.game.players[0]

        self.log(f"\n🎡 {player.name} plays Wheel of Fortune!")

        # Remove the card from hand
        if card in player.hand:
            player.hand.remove(card)
            self.game.removed_pile.append(card)

        # Ensure enough cards available
        self.game.ensure_cards_available(4)

        # Draw 4 cards
        drawn_cards = []
        for _ in range(4):
            drawn_card = self.game.draw_pile.draw()
            drawn_cards.append(drawn_card)

        self.log(f"Drew 4 cards: {drawn_cards}")

        # Create dialog to choose which cards to keep
        dialog = tk.Toplevel(self.root)
        dialog.title("Wheel of Fortune - Choose Cards to Keep")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Select which cards to keep:",
                 font=('Arial', 10, 'bold')).pack(pady=10)

        tk.Label(dialog, text=f"Your current hand: {player.hand}",
                 font=('Arial', 9)).pack(pady=5)

        # Checkboxes for each drawn card
        check_vars = []
        for i, drawn_card in enumerate(drawn_cards):
            var = tk.BooleanVar(value=True)  # Default to keeping all
            check_vars.append(var)
            value, _ = calculate_hand_value([drawn_card])
            cb = tk.Checkbutton(dialog, text=f"{drawn_card} (value: {value})", variable=var)
            cb.pack(anchor=tk.W, padx=20)

        def confirm():
            kept_cards = []
            discarded_cards = []

            for i, var in enumerate(check_vars):
                if var.get():
                    kept_cards.append(drawn_cards[i])
                else:
                    discarded_cards.append(drawn_cards[i])

            # Add kept cards to hand
            player.hand.extend(kept_cards)

            # Discard the rest
            self.game.discard_pile.extend(discarded_cards)

            self.log(f"Kept: {kept_cards}")
            if discarded_cards:
                self.log(f"Discarded: {discarded_cards}")

            dialog.destroy()
            self.update_display()
            self.update_buttons()

        def keep_all():
            for var in check_vars:
                var.set(True)

        def keep_none():
            for var in check_vars:
                var.set(False)

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Select All", command=keep_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Select None", command=keep_none).pack(side=tk.LEFT, padx=5)

        tk.Button(dialog, text="Confirm", command=confirm).pack(pady=10)

    def play_moon_effect(self, card):
        """GUI handler for The Moon effect"""
        player = self.game.players[0]

        self.log(f"\n🌙 {player.name} plays The Moon!")

        # Remove the card from hand
        if card in player.hand:
            player.hand.remove(card)
            self.game.removed_pile.append(card)

        # Deal a new community card
        self.game.ensure_cards_available(1)
        new_card = self.game.draw_pile.draw()
        self.game.community_cards.append(new_card)

        self.log(f"Dealer adds {new_card} to the community cards.")
        self.log(f"Community cards: {self.game.community_cards}")

        # Update display
        self.update_display()
        self.update_buttons()

        messagebox.showinfo("The Moon",
            f"A new community card has been dealt:\n{new_card}\n\n"
            f"Community cards are now:\n{self.game.community_cards}")

    def play_sun_effect(self, card):
        """GUI handler for The Sun effect"""
        player = self.game.players[0]

        self.log(f"\n☀️ {player.name} plays The Sun!")
        self.log("All players must now play with their hands face up!")

        # Set the flag - hands are now visible
        self.game.hands_face_up = True

        # The Sun stays in hand (stays_in_hand=True in registry)
        # So we don't remove the card

        # Log all hands
        self.log("\n=== ALL HANDS REVEALED ===")
        revealed_info = []
        for p in self.game.players:
            if not p.has_folded:
                value, busted = calculate_hand_value(p.hand)
                status = "[BUSTED]" if busted else "[OK]"
                self.log(f"{p.name}: {p.hand} = {value} {status}")
                revealed_info.append(f"{p.name}: {value} {status}")
        self.log("=" * 30)

        # Update display - opponent cards will now show face up
        self.update_display()
        self.update_buttons()

        messagebox.showinfo("The Sun",
            "All hands are now revealed!\n\n" +
            "\n".join(revealed_info))

    def play_judgment_effect(self, card):
        """GUI handler for The Last Judgment effect"""
        player = self.game.players[0]

        self.log(f"\n⚖️ {player.name} plays The Last Judgment!")
        self.log("The hand immediately ends and advances to showdown!")

        # Remove the card from hand
        if card in player.hand:
            player.hand.remove(card)
            self.game.removed_pile.append(card)

        # Set the flag
        self.game.judgment_played = True

        # Show message before showdown
        messagebox.showinfo("The Last Judgment",
            "The hand ends immediately!\n"
            "Advancing to showdown...")

        # Go directly to showdown
        self.do_showdown()

    def play_universe_effect(self, card):
        """GUI handler for The Universe effect"""
        player = self.game.players[0]

        self.log(f"\n🌌 {player.name} plays The Universe - See the Future!")

        # Remove the card from hand
        if card in player.hand:
            player.hand.remove(card)
            self.game.removed_pile.append(card)

        # Check if enough cards
        if len(self.game.draw_pile.cards) < 6:
            messagebox.showwarning("The Universe",
                "Not enough cards in the draw pile to use this effect.")
            self.update_display()
            self.update_buttons()
            return

        # Peek at top 6 cards (don't remove them)
        top_6 = self.game.draw_pile.cards[:6]

        self.log("You peek at the top 6 cards of the draw pile...")

        # Create dialog to show the cards
        dialog = tk.Toplevel(self.root)
        dialog.title("The Universe - See the Future")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="🌌 The Top 6 Cards 🌌",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        tk.Label(dialog, text="(In order from top to bottom - don't show anyone!)",
                 font=('Arial', 9, 'italic')).pack(pady=5)

        # Show each card with its value
        for i, peek_card in enumerate(top_6):
            value, _ = calculate_hand_value([peek_card])
            tk.Label(dialog, text=f"{i+1}. {peek_card} (value: {value})",
                     font=('Arial', 11)).pack(anchor=tk.W, padx=30)

        def close():
            dialog.destroy()
            self.update_display()
            self.update_buttons()

        tk.Button(dialog, text="Got it!", command=close, width=15).pack(pady=20)

    def end_player_turn(self):
        """End the current player's turn and move to next"""
        player = self.game.players[0]

        # Mark that we want to ask about discard after draw for human player
        if 'draw_action' in self.current_player_action:
            self.current_player_action['ask_discard_after_draw'] = True

        # Execute the turn
        still_active = self.game.execute_player_turn(player, self.current_player_action)

        # Clear action
        self.current_player_action = {}

        # Update display
        self.update_display()

        # Update buttons immediately to disable them if player folded
        self.update_buttons()

        # Check if betting round is complete
        if self.game.is_betting_round_complete():
            self.log("\nBetting round complete!")
            self.set_turn_waiting("Round Complete")
            self.root.after(1000, self.advance_to_next_phase)
        else:
            # Let AI players take their turns
            self.set_turn_waiting("AI Playing...")
            self.root.after(1000, self.process_ai_turns)

    def process_ai_turns(self):
        """Process all AI player turns"""
        for player in self.game.players[1:]:
            if not player.has_folded and player.credits > 0 and not player.has_acted:
                # Show AI indicator
                self.set_turn_ai(player.name)
                self.root.update()  # Force UI update

                # Get AI action
                action = get_simple_ai_action(self.game, player)

                # Execute turn
                self.game.execute_player_turn(player, action)

                # Log action
                bet_action = action.get('bet_action', 'unknown')
                self.log(f"{player.name} {bet_action}s")

        # Update display
        self.update_display()

        # Check if round complete
        if self.game.is_betting_round_complete():
            self.log("\nBetting round complete!")
            self.set_turn_waiting("Round Complete")
            self.root.after(1000, self.advance_to_next_phase)
        else:
            # Back to player
            self.update_buttons()

    def advance_to_next_phase(self):
        """Advance to the next phase of the hand"""
        # Check if only one player remains
        active_players = self.game.get_active_players()
        if len(active_players) <= 1:
            self.do_showdown()
            return

        if self.current_phase == 'flop':
            # Deal turn card
            self.game.deal_turn()
            self.current_phase = 'turn'
            self.log(f"\nTurn: {self.game.community_cards}")

        elif self.current_phase == 'turn':
            # Deal river card
            self.game.deal_river()
            self.current_phase = 'river'
            self.log(f"\nRiver: {self.game.community_cards}")

        elif self.current_phase == 'river':
            # Go to showdown
            self.do_showdown()
            return

        # Reset for new betting round
        self.game.reset_for_betting_round()
        self.current_player_action = {}

        # Update display
        self.update_display()

        # Start new betting round
        self.log("\nYour turn! Place your bet.")
        self.update_buttons()

    def do_showdown(self):
        """Handle the showdown phase"""
        self.current_phase = 'showdown'
        self.set_turn_waiting("Showdown")
        self.log("\n=== SHOWDOWN ===")

        active_players = self.game.get_active_players()

        # Show all hands
        for player in active_players:
            value, busted = calculate_hand_value(player.hand)
            status = " [BUSTED]" if busted else ""
            self.log(f"{player.name}: {player.hand} = {value}{status}")

        # Determine winner
        winner = self.game.determine_winner()

        if winner:
            value, _ = calculate_hand_value(winner.hand)

            # Check if a tiebreaker was used
            if self.game.tiebreaker_info:
                tb_info = self.game.tiebreaker_info
                tied_str = " and ".join(tb_info['tied_players'])
                values_str = ", ".join(str(v) for v in tb_info['tied_values'])

                self.log(f"\nTIE: {tied_str} are tied with values {values_str}")

                if tb_info['type'] == 'high_card':
                    self.log(f"TIEBREAKER: {winner.name} wins by high card (value {tb_info['winner_high_card']})!")
                elif tb_info['type'] == 'suit':
                    self.log(f"TIEBREAKER: {winner.name} wins by suit ({tb_info['winner_suit']})!")
            else:
                self.log(f"\n{winner.name} wins with a hand value of {value}!")

            self.game.award_pot(winner)
            self.log(f"{winner.name} now has {winner.credits} credits.")
        else:
            self.log("\nNo winner - everyone busted!")
            self.game.pot = 0

        # Advance dealer
        self.game.advance_dealer()

        # Update display
        self.update_display()

        # Check if game should continue
        players_with_credits = [p for p in self.game.players if p.credits > 0]
        if len(players_with_credits) <= 1:
            if players_with_credits:
                self.log(f"\n=== GAME OVER ===")
                self.log(f"{players_with_credits[0].name} wins the game!")
            else:
                self.log(f"\n=== GAME OVER ===")
                self.log("Everyone is out of credits!")
        else:
            # Ask to continue
            self.root.after(2000, self.prompt_new_hand)

    def prompt_new_hand(self):
        """Prompt user to start a new hand"""
        if messagebox.askyesno("New Hand", "Start a new hand?"):
            self.start_new_hand()

    def show_rules(self):
        """Show game rules"""
        rules = """Sabacc con i Tarocchi Rules:

Goal: Get as close to 23 (or -23) as possible without going over.

Each hand has three betting rounds:
1. After the flop (3 community cards)
2. After the turn (4th community card)
3. After the river (5th community card)

On your turn, you can:
- Bet (Fold, Call, or Raise)
- Draw a card (from draw pile, discard pile, or swap with community)
- Discard a card
- Play a Trionfi special card

Special Trionfi cards have unique effects!
"""
        messagebox.showinfo("Rules", rules)

    def show_about(self):
        """Show about dialog"""
        about = """Sabacc con i Tarocchi
Version 1.0

A card game blending poker betting,
rummy-style draws, and blackjack scoring.

© 2025 The Boreas Press
"""
        messagebox.showinfo("About", about)


def main():
    root = tk.Tk()
    app = SabaccGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()