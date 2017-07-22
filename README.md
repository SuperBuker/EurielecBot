# EurielecBot
[@EurielecBot](https://t.me/eurielecbot) the [Eurielec - EESTEC LC Madrid](https://eurielec.etsit.upm.es "Eurielec's Homepage") Telegram Bot

The aim of this Telegram bot is to enhance the capabilities and functionalities of the internal chat group. We wanted something funny and useful in our daily work as student association.

The project is based on [Flask](http://flask.pocoo.org/) and [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) and entirely written on Python 3.
The integration with [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) is possible and requires some minor fixes that aren't yet documented, because it's a work in progress.

The IP Camera functionalities are based on the [Ingenic XBurst T10 SoC](http://www.ingenic.com/en/?product/id/11.html) platform, ensuring compatibility with more than 1250 different camera models.
The multimedia adaptations are achieved through [FFmpeg](https://www.ffmpeg.org/) transcoding. Some fine tunning can be done at this point if encoding hardware is available.
The speech-to-text service is based on [Wit.ai](https://wit.ai/) cloud service, and requires a different token for every language supported. This functionality still experimental.

Copyright (C) 2017
Jorge Díez de la Fuente <buker(at)stuker.es>
