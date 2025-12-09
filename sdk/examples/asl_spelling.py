#!/usr/bin/env python3
# Copyright 2025 TetherIA, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ASL Spelling Script for TetherIA Robotic Hand

This script controls the robotic hand to spell words using American Sign Language (ASL).
Joint order: [thumb_rot, thumb_mcp, thumb_ip, index, middle, ring, pinky]
Values are in degrees (0 = open/extended, higher = closed/flexed)
"""

from aero_open_sdk.aero_hand import AeroHand
import time
import sys
import argparse
import serial.tools.list_ports

# ASL Letter Positions
# Format: [thumb_rotation, thumb_mcp, thumb_ip, index, middle, ring, pinky]
ASL_POSITIONS = {
    'A': [50.0, 80.0, 60.0, 90.0, 90.0, 90.0, 90.0],  # Closed fist, thumb alongside
    'B': [80.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Flat hand, thumb tucked
    'C': [30.0, 30.0, 20.0, 40.0, 40.0, 40.0, 40.0],  # Curved hand
    'D': [75.0, 40.0, 30.0, 0.0, 90.0, 90.0, 90.0],  # Index up, others closed
    'E': [50.0, 60.0, 50.0, 70.0, 70.0, 70.0, 70.0],  # All fingers curled down
    'F': [60.0, 50.0, 40.0, 60.0, 0.0, 0.0, 0.0],  # Index-thumb touch, others up
    'G': [90.0, 20.0, 10.0, 10.0, 90.0, 90.0, 90.0],  # Index pointing, thumb out
    'H': [90.0, 20.0, 10.0, 10.0, 10.0, 90.0, 90.0],  # Index+middle pointing
    'I': [80.0, 20.0, 10.0, 90.0, 90.0, 90.0, 0.0],  # Pinky up
    'J': [80.0, 20.0, 10.0, 90.0, 90.0, 90.0, 0.0],  # Pinky up (motion added later)
    'K': [45.0, 30.0, 20.0, 0.0, 20.0, 90.0, 90.0],  # Index+middle up, thumb between
    'L': [0.0, 0.0, 0.0, 0.0, 90.0, 90.0, 90.0],  # Index+thumb L-shape
    'M': [80.0, 40.0, 30.0, 30.0, 30.0, 30.0, 90.0],  # Three fingers over thumb
    'N': [80.0, 40.0, 30.0, 30.0, 30.0, 90.0, 90.0],  # Two fingers over thumb
    'O': [50.0, 50.0, 40.0, 50.0, 50.0, 50.0, 50.0],  # All fingers forming circle
    'P': [45.0, 20.0, 10.0, 10.0, 90.0, 90.0, 90.0],  # Index down, thumb out
    'Q': [30.0, 10.0, 0.0, 70.0, 90.0, 90.0, 90.0],  # Index+thumb pointing down
    'R': [70.0, 30.0, 20.0, 5.0, 5.0, 90.0, 90.0],  # Index+middle crossed
    'S': [50.0, 80.0, 60.0, 90.0, 90.0, 90.0, 90.0],  # Fist with thumb over fingers
    'T': [70.0, 60.0, 50.0, 40.0, 90.0, 90.0, 90.0],  # Thumb between index+middle
    'U': [80.0, 20.0, 10.0, 0.0, 0.0, 90.0, 90.0],  # Index+middle together, up
    'V': [80.0, 20.0, 10.0, 0.0, 0.0, 90.0, 90.0],  # Index+middle apart, up
    'W': [80.0, 20.0, 10.0, 0.0, 0.0, 0.0, 90.0],  # Three fingers up
    'X': [70.0, 40.0, 30.0, 40.0, 90.0, 90.0, 90.0],  # Index bent, hook shape
    'Y': [0.0, 0.0, 0.0, 90.0, 90.0, 90.0, 0.0],  # Thumb+pinky out (shaka)
    'Z': [90.0, 20.0, 10.0, 0.0, 90.0, 90.0, 90.0],  # Index up (trace Z motion)

    # Special positions
    'NEUTRAL': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Open palm
    'SPACE': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Open palm for word breaks
}


def find_aero_hand_port():
    """
    Auto-detect the COM port for the TetherIA Aero Hand
    
    Looks for Espressif ESP32-S3 devices with VID:PID 303A:1001
    
    Returns:
        str: Port name if found, None otherwise
    """
    AERO_HAND_VID = 0x303A  # Espressif Systems
    AERO_HAND_PID = 0x1001  # ESP32-S3 USB-OTG
    
    print("Scanning for TetherIA Aero Hand...")
    
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if port.vid == AERO_HAND_VID and port.pid == AERO_HAND_PID:
            print(f"Found Aero Hand on: {port.device}")
            print(f"  VID:PID = {port.vid:04X}:{port.pid:04X}")
            return port.device
    
    print("No Aero Hand found. Available ports:")
    for port in ports:
        if port.vid:
            print(f"  {port.device}: VID:PID = {port.vid:04X}:{port.pid:04X}")
        else:
            print(f"  {port.device}: {port.description}")
    
    return None


class ASLSpeller:
    """Controls the robotic hand to spell words in ASL"""

    def __init__(self, port=None):
        """
        Initialize the ASL Speller

        Args:
            port: Serial port for the hand. If None, auto-detect the Aero Hand
        """
        if port is None:
            port = find_aero_hand_port()
            if port is None:
                raise Exception("Could not find TetherIA Aero Hand. Please specify port manually with -p/--port")
        
        print(f"Connecting to hand on {port}...")
        self.hand = AeroHand(port)
        print("Connected!")

    def spell_letter(self, letter, hold_time=1.5):
        """
        Spell a single letter in ASL

        Args:
            letter: Letter to spell (A-Z)
            hold_time: How long to hold the position (seconds)
        """
        letter = letter.upper()

        if letter == ' ':
            letter = 'SPACE'

        if letter not in ASL_POSITIONS:
            print(f"Warning: Letter '{letter}' not implemented, skipping...")
            return

        position = ASL_POSITIONS[letter]
        print(f"Signing: {letter}")

        # Create trajectory with transition and hold
        trajectory = [
            (position, 0.8),  # Move to position
            (position, hold_time),  # Hold position
        ]

        self.hand.run_trajectory(trajectory)

    def spell_word(self, word, letter_delay=1.5, word_delay=2.0):
        """
        Spell an entire word in ASL

        Args:
            word: Word to spell
            letter_delay: Time to hold each letter (seconds)
            word_delay: Time to pause after the word (seconds)
        """
        print(f"\n{'='*50}")
        print(f"Spelling: {word.upper()}")
        print(f"{'='*50}\n")

        # Return to neutral position first
        self.hand.run_trajectory([(ASL_POSITIONS['NEUTRAL'], 0.5)])
        time.sleep(0.3)

        # Spell each letter
        for letter in word:
            if letter == ' ':
                print("--- SPACE ---")
                self.hand.run_trajectory([(ASL_POSITIONS['SPACE'], word_delay)])
            else:
                self.spell_letter(letter, hold_time=letter_delay)
                time.sleep(0.3)  # Small pause between letters

        # Return to neutral
        print("\nReturning to neutral position...")
        self.hand.run_trajectory([(ASL_POSITIONS['NEUTRAL'], 0.8)])
        time.sleep(word_delay)
        print(f"Finished spelling: {word.upper()}\n")

    def spell_sentence(self, sentence, letter_delay=1.5, word_delay=2.0):
        """
        Spell multiple words (sentence) in ASL

        Args:
            sentence: Sentence to spell
            letter_delay: Time to hold each letter (seconds)
            word_delay: Time to pause between words (seconds)
        """
        words = sentence.split()

        print(f"\n{'*'*50}")
        print(f"Spelling sentence: {sentence.upper()}")
        print(f"Total words: {len(words)}")
        print(f"{'*'*50}\n")

        for i, word in enumerate(words, 1):
            print(f"Word {i}/{len(words)}")
            self.spell_word(word, letter_delay=letter_delay, word_delay=word_delay)

        print(f"\n{'*'*50}")
        print(f"Finished spelling sentence!")
        print(f"{'*'*50}\n")

    def demo_alphabet(self, letter_delay=2.0):
        """
        Demonstrate all letters A-Z

        Args:
            letter_delay: Time to hold each letter (seconds)
        """
        print("\n" + "="*50)
        print("ASL ALPHABET DEMONSTRATION")
        print("="*50 + "\n")

        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for letter in alphabet:
            self.spell_letter(letter, hold_time=letter_delay)
            time.sleep(0.5)

        # Return to neutral
        print("\nReturning to neutral position...")
        self.hand.run_trajectory([(ASL_POSITIONS['NEUTRAL'], 1.0)])
        print("Alphabet demo complete!\n")


def main():
    """Main function with example usage"""

    parser = argparse.ArgumentParser(
        description='ASL Spelling System for TetherIA Robotic Hand',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p COM11 "HELLO WORLD"   # Spell "HELLO WORLD" on COM11
  %(prog)s -p COM3 demo             # Show alphabet demo on COM3
  %(prog)s -p COM11 HELLO           # Spell single word "HELLO"
  %(prog)s -p /dev/ttyUSB0          # Interactive mode on Linux
  %(prog)s                          # Interactive mode on default port (COM11)
        """
    )

    parser.add_argument(
        '-p', '--port',
        default=None,
        help='Serial port for the robotic hand (default: auto-detect)'
    )
    parser.add_argument(
        'text',
        nargs='?',
        help='Text to spell (use quotes for multiple words), or "demo" to show alphabet'
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("ASL SPELLING SYSTEM FOR TETHERIA ROBOTIC HAND")
    print("="*60)

    try:
        speller = ASLSpeller(port=args.port)

        # Check if text was provided
        if args.text:
            # Command line argument provided
            text = args.text

            if text.lower() == "demo":
                speller.demo_alphabet(letter_delay=1.5)
            else:
                speller.spell_sentence(text, letter_delay=1.5, word_delay=2.0)
        else:
            # Interactive prompt
            print("\nASL Speller Ready!")
            print("Commands:")
            print("  - Type a word or sentence to spell it")
            print("  - Type 'demo' to see the full alphabet")
            print("  - Type 'quit' or 'exit' to exit")
            print("-" * 60)

            while True:
                try:
                    text = input("\nEnter text to spell (or 'quit'): ").strip()

                    if text.lower() in ['quit', 'exit', 'q']:
                        print("Exiting ASL Speller...")
                        break

                    if not text:
                        continue

                    if text.lower() == 'demo':
                        speller.demo_alphabet(letter_delay=1.5)
                    else:
                        speller.spell_sentence(text, letter_delay=1.5, word_delay=2.0)

                except KeyboardInterrupt:
                    print("\n\nInterrupted by user. Exiting...")
                    break

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Check that the hand is connected")
        print("  2. Verify the correct serial port with -p/--port")
        print("  3. Make sure no other program is using the port")
        return 1

    print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    exit(main())
