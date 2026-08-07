def expectancy(win_rate,
               average_win,
               average_loss):

    return (

        win_rate

        * average_win

    ) - (

        (1 - win_rate)

        * average_loss

    )