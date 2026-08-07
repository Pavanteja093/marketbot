class TradeSetup:

    def create(

        self,

        recommendation

    ):

        return {

            "signal":
                recommendation["signal"],

            "position":
                recommendation["position_size"],

            "stop_loss":
                None,

            "target":
                None

        }