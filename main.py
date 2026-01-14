import re
import unittest
import uuid
from abc import ABCMeta, abstractmethod
from typing import Self


class UsernameException(Exception):
    pass


class PaymentException(Exception):
    SAME_USER_ERROR = "User cannot pay themselves."
    INSUFFICIENT_BALANCE_ERROR = "Insufficient balance to make the payment."
    INVALID_AMOUNT_ERROR = "Amount must be a non-negative number."
    INVALID_AMOUNT_NUMBER_ERROR = "Amount must be a valid number."
    NO_CREDIT_CARD_ERROR = "Must have a credit card to make a payment."


class CreditCardException(Exception):
    MULTIPLE_CREDIT_CARDS_ERROR = "Only one credit card per user!"
    INVALID_CREDIT_CARD_ERROR = "Invalid credit card number."


class FeedLog(metaclass=ABCMeta):
    @abstractmethod
    def get_feed_msg(self) -> str:
        pass


class Payment(FeedLog):

    def __init__(self, amount: float, actor: "User", target: "User", note: str):
        self.id = str(uuid.uuid4())
        self.amount = float(amount)
        self.actor = actor
        self.target = target
        self.note = note

    def get_feed_msg(self) -> str:
        return f"{self.actor.username} paid {self.target.username} ${self.amount:.2f} for {self.note}"


class FriendshipLog(FeedLog):
    STATUS_ADDED = "added"
    STATUS_REMOVED = "removed"

    def __init__(self, user1: "User", user2: "User", status: str):
        self.id = str(uuid.uuid4())
        self.user1 = user1
        self.user2 = user2
        self.status = status

    def get_feed_msg(self) -> str:
        return f"{self.user1.username} {self.status} {self.user2.username} as a friend."


class User:

    def __init__(self, username: str):
        self.credit_card_number: str | None = None
        self.balance: float = 0.0
        self.feed: list[Payment | FriendshipLog] = []
        self.friends: list[User] = []

        if self._is_valid_username(username):
            self.username = username
        else:
            raise UsernameException("Username not valid.")

    def retrieve_feed(self):
        return [feed_item.get_feed_msg() for feed_item in self.feed]

    def add_friend(self, new_friend: Self):
        self.friends.append(new_friend)
        friendship_log = FriendshipLog(self, new_friend, FriendshipLog.STATUS_ADDED)
        self.feed.append(friendship_log)
        new_friend.feed.append(friendship_log)

    def add_to_balance(self, amount: float | str):
        amount = float(amount)
        if amount <= 0.0:
            raise ValueError("Amount must be a non-negative number.")
        self.balance += amount

    def add_credit_card(self, credit_card_number):
        if self.credit_card_number is not None:
            raise CreditCardException(CreditCardException.MULTIPLE_CREDIT_CARDS_ERROR)

        if self._is_valid_credit_card(credit_card_number):
            self.credit_card_number = credit_card_number

        else:
            raise CreditCardException()

    def pay(self, target: Self, amount: float, note: str) -> Payment:
        try:
            amount = float(amount)
        except ValueError:
            raise PaymentException(PaymentException.INVALID_AMOUNT_NUMBER_ERROR)

        if amount <= 0.0:
            raise PaymentException(PaymentException.INVALID_AMOUNT_ERROR)

        if self.balance >= amount:
            payment = self.pay_with_balance(target, amount, note)
        else:
            payment = self.pay_with_card(target, amount, note)

        self.feed.append(payment)
        target.feed.append(payment)

        return payment

    def pay_with_card(self, target, amount, note):
        amount = float(amount)

        if self.username == target.username:
            raise PaymentException(PaymentException.SAME_USER_ERROR)

        elif amount <= 0.0:
            raise PaymentException(PaymentException.INVALID_AMOUNT_ERROR)

        elif self.credit_card_number is None:
            raise PaymentException(PaymentException.NO_CREDIT_CARD_ERROR)

        self._charge_credit_card(self.credit_card_number)
        payment = Payment(amount, self, target, note)
        target.add_to_balance(amount)

        return payment

    def pay_with_balance(self, target: Self, amount: float, note: str) -> Payment:
        if self.username == target.username:
            raise PaymentException(PaymentException.SAME_USER_ERROR)

        elif amount <= 0.0:
            raise PaymentException(PaymentException.INVALID_AMOUNT_ERROR)

        elif self.balance < amount:
            raise PaymentException(PaymentException.INSUFFICIENT_BALANCE_ERROR)

        self.balance -= amount
        payment = Payment(amount, self, target, note)
        target.add_to_balance(amount)
        return payment

    def _is_valid_credit_card(self, credit_card_number):
        return credit_card_number in ["4111111111111111", "4242424242424242"]

    def _is_valid_username(self, username):
        return re.match("^[A-Za-z0-9_\\-]{4,15}$", username)

    def _charge_credit_card(self, credit_card_number: str):
        # magic method that charges a credit card thru the card processor
        pass


class MiniVenmo:
    def create_user(self, username, balance, credit_card_number):
        user = User(username)
        user.add_to_balance(balance)
        user.add_credit_card(credit_card_number)
        return user

    def render_feed(self, feed):
        for payment_msg in feed:
            print(payment_msg)

    @classmethod
    def run(cls):
        venmo = cls()

        bobby = venmo.create_user("Bobby", 5.00, "4111111111111111")
        carol = venmo.create_user("Carol", 10.00, "4242424242424242")

        try:
            # should complete using balance
            bobby.pay(carol, 5.00, "Coffee")

            # should complete using card
            carol.pay(bobby, 15.00, "Lunch")
        except PaymentException as e:
            print(e)

        feed = bobby.retrieve_feed()
        venmo.render_feed(feed)

        bobby.add_friend(carol)


class TestUser(unittest.TestCase):

    def test_user_create(self):
        name = "Bobby"
        self.assertEqual(User(name).username, name)

    def test_user_create_invalid_username(self):
        with self.assertRaises(UsernameException):
            User("Invalid Bobby!")

    def test_user_add_to_balance(self):
        bobby = User("Bobby")
        bobby.add_to_balance(10.00)
        self.assertEqual(bobby.balance, 10.00)

    def test_user_add_to_balance_invalid_amounts(self):
        bobby = User("Bobby")

        with self.assertRaises(ValueError):
            bobby.add_to_balance(0.0)
        with self.assertRaises(ValueError):
            bobby.add_to_balance(-5.00)
        with self.assertRaises(ValueError):
            bobby.add_to_balance("five")

        bobby.add_to_balance("5.0")
        self.assertEqual(bobby.balance, 5.0)

    def test_user_pay_with_balance(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_to_balance(10.00)

        payment = bobby.pay_with_balance(carol, 5.00, "Coffee")

        self.assertEqual(payment.amount, 5.00)
        self.assertEqual(payment.actor.username, "Bobby")
        self.assertEqual(payment.target.username, "Carol")
        self.assertEqual(payment.note, "Coffee")

        self.assertEqual(bobby.balance, 5.00)
        self.assertEqual(carol.balance, 5.00)

    def test_user_pay_with_balance_same_user(self):
        bobby = User("Bobby")
        bobby.add_to_balance(10.00)

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_balance(bobby, 5.00, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.SAME_USER_ERROR)

    def test_user_pay_with_balance_invalid_amounts(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_to_balance(10.00)

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_balance(carol, 0.0, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.INVALID_AMOUNT_ERROR)

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_balance(carol, -5.00, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.INVALID_AMOUNT_ERROR)

    def test_user_pay_with_balance_insufficient_funds(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_to_balance(5.00)

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_balance(carol, 10.00, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.INSUFFICIENT_BALANCE_ERROR)

    def test_user_pay(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_credit_card("4111111111111111")
        bobby.add_to_balance(10.00)

        payment = bobby.pay(carol, 5.00, "Coffee")

        self.assertEqual(payment.amount, 5.00)
        self.assertEqual(payment.actor.username, "Bobby")
        self.assertEqual(payment.target.username, "Carol")
        self.assertEqual(payment.note, "Coffee")

        self.assertEqual(bobby.balance, 5.00)
        self.assertEqual(carol.balance, 5.00)

    def test_user_pay_with_card(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_credit_card("4111111111111111")

        payment = bobby.pay_with_card(carol, 15.00, "Lunch")

        self.assertEqual(payment.amount, 15.00)
        self.assertEqual(payment.actor.username, "Bobby")
        self.assertEqual(payment.target.username, "Carol")
        self.assertEqual(payment.note, "Lunch")

        self.assertEqual(bobby.balance, 0.0)
        self.assertEqual(carol.balance, 15.00)

    def test_user_pay_with_card_same_user(self):
        bobby = User("Bobby")
        bobby.add_credit_card("4111111111111111")

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_card(bobby, 5.00, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.SAME_USER_ERROR)

    def test_user_pay_with_card_invalid_amounts(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_credit_card("4111111111111111")

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_card(carol, 0.0, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.INVALID_AMOUNT_ERROR)

        with self.assertRaises(PaymentException) as exc:
            bobby.pay_with_card(carol, -5.00, "Coffee")
            self.assertEqual(str(exc.exception), PaymentException.INVALID_AMOUNT_ERROR)

    def test_user_retrieve_feed(self):
        bobby, carol = User("Bobby"), User("Carol")
        bobby.add_credit_card("4111111111111111")
        bobby.add_to_balance(10.00)

        bobby.pay(carol, 5.00, "Coffee")
        carol.add_credit_card("4242424242424242")
        carol.pay(bobby, 15.00, "Lunch")

        feed = bobby.retrieve_feed()
        self.assertEqual(len(feed), 2)
        self.assertIn("Bobby paid Carol $5.00 for Coffee", feed)
        self.assertIn("Carol paid Bobby $15.00 for Lunch", feed)


class TestMiniVenmo(unittest.TestCase):

    def test_mini_venmo_create_user(self):
        bobby_data = {
            "username": "Bobby",
            "balance": 5.00,
            "credit_card_number": "4111111111111111",
        }
        mini_venmo = MiniVenmo()
        bobby = mini_venmo.create_user(**bobby_data)
        self.assertEqual(bobby.username, bobby_data["username"])
        self.assertEqual(bobby.balance, bobby_data["balance"])
        self.assertEqual(bobby.credit_card_number, bobby_data["credit_card_number"])

    def test_mini_venmo_render_feed(self):
        mini_venmo = MiniVenmo()
        expected_feed_msg = [
            "Bobby paid Carol $5.00 for Coffee",
            "Carol paid Bobby $15.00 for Lunch",
        ]

        bobby = mini_venmo.create_user("Bobby", 5.00, "4111111111111111")
        carol = mini_venmo.create_user("Carol", 10.00, "4242424242424242")
        bobby.pay(carol, 5.00, "Coffee")
        carol.pay(bobby, 15.00, "Lunch")
        feed = bobby.retrieve_feed()
        self.assertEqual(feed, expected_feed_msg)

        bobby.add_friend(carol)
        expected_feed_msg.append("Bobby added Carol as a friend.")
        feed = bobby.retrieve_feed()
        self.assertEqual(feed, expected_feed_msg)


if __name__ == "__main__":
    unittest.main(verbosity=3)
