from django.conf import settings

class PaymentGatewayService:
    def create_payment(self, transaction_id, amount, customer_details):
        if settings.DEBUG:
            print("--- MOCK PAYMENT GATEWAY ---")
            print(f"Creating payment for Transaction ID: {transaction_id}")
            print(f"Amount: {amount}")
            print(f"Customer: {customer_details}")
            print("----------------------------")
            return True, f"https://mock-payment.com/pay/{transaction_id}"
        return False, "Not implemented"

    def release_escrow(self, transaction_id):
        if settings.DEBUG:
            print("--- MOCK PAYMENT GATEWAY ---")
            print(f"Releasing escrow for Transaction ID: {transaction_id}")
            print("----------------------------")
            return True, "Escrow released successfully."
        return False, "Not implemented"