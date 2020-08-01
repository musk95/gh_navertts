import asyncio
import logging
import time

import async_timeout
from urllib import parse

from homeassistant.components.tts import CONF_LANG, PLATFORM_SCHEMA, Provider
from .const import CONF_VOICE, CONF_SPEED
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import HTTP_OK, HTTP_INTERNAL_SERVER_ERROR
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SUPPORT_LANGUAGES = ["ko"]
DEFAULT_LANG = "ko"

SUPPORT_VOICE = ["nara", "kyuri", "jinho", "mijin", "clara", "matt", "yuri", "shinji", "meimei", "liangliang", "jose", "carmen", "dsangjin", "djiyun", "dinna"]
DEFAULT_VOICE = "dinna"

DEFAULT_SPEED = 0
DEFAULT_PORT = 30010

MESSAGE_SIZE = 148

GH_NAVER_SPEECH_URL = "/googleHome/api/naverTTS/"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_LANG, default=DEFAULT_LANG): vol.In(SUPPORT_LANGUAGES),
        vol.Optional(CONF_VOICE, default=DEFAULT_VOICE): vol.In(SUPPORT_VOICE),
        vol.Optional(CONF_SPEED, default=DEFAULT_SPEED): vol.All(
            vol.Coerce(int), vol.Range(min=-10, max=10)
        )
    }
)

async def async_get_engine(hass, config, discovery_info=None):
    """Set up GH naver speech component."""
    return GHNaverProvider(hass, config[CONF_HOST], config[CONF_PORT], config[CONF_VOICE], config[CONF_SPEED])

class GHNaverProvider(Provider):
    """The GH Naver speech API provider."""

    def __init__(self, hass, host, port, voice, speed):
        """Init Google TTS service."""
        self.hass = hass
        self._host = host
        self._port = port
        self._voice = voice
        self._speed = speed
        self._lang = DEFAULT_LANG

    @property
    def default_language(self):
        """Return the default language."""
        return self._lang

    @property
    def supported_languages(self):
        """Return list of supported languages."""
        return SUPPORT_LANGUAGES

    async def async_get_tts_audio(self, message, language, options=None):
        """Load TTS from google."""
        websession = async_get_clientsession(self.hass)
        #message_parts = self._split_message_to_parts(message)

        #for idx, part in enumerate(message_parts):
        #    _LOGGER.error("idx:%d, part:%s", idx, part)

        data = b""

        url_param = {
            "voice":self._voice,
            "speed":self._speed
        }

        url = "http://"+self._host+":"+str(self._port)+GH_NAVER_SPEECH_URL+parse.quote(message)
        _LOGGER.debug("URL:%s", url)

        try:
            with async_timeout.timeout(60):
                request = await websession.get(
                    url, params=url_param
                )

                if request.status == HTTP_INTERNAL_SERVER_ERROR:
                    time.sleep(1)
                    request = await websession.get(
                        url, params=url_param
                    )

                if request.status != HTTP_OK:
                    _LOGGER.error(
                        "Error %d on load URL %s", request.status, request.url
                    )
                    return None, None
                data += await request.read()

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Timeout for google speech")
            return None, None

        return "mp3", data

    @staticmethod
    def _split_message_to_parts(message):
        """Split message into single parts."""
        if len(message) <= MESSAGE_SIZE:
            return [message]

        punc = "!()[]?.,;:"
        punc_list = [re.escape(c) for c in punc]
        pattern = "|".join(punc_list)
        parts = re.split(pattern, message)

        def split_by_space(fullstring):
            """Split a string by space."""
            if len(fullstring) > MESSAGE_SIZE:
                idx = fullstring.rfind(" ", 0, MESSAGE_SIZE)
                return [fullstring[:idx]] + split_by_space(fullstring[idx:])
            return [fullstring]

        msg_parts = []
        for part in parts:
            msg_parts += split_by_space(part)

        return [msg for msg in msg_parts if len(msg) > 0]
