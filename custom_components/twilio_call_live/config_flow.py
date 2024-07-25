"""Config flow for Twilio."""

from math import floor
import re
import logging
from typing import Any, Awaitable, Callable, Coroutine
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_EVENT
import voluptuous as vol
import json
from .const import (
    SYS_EVENT,
    SYS_EVENT_INDEX,
    SYS_PHRASE,
    SYS_PHRASE_INDEX,
)

from .config import EventPhrases, EventPhrasesList, SystemValues
from .const import (
    CONF_ACTION,
    CONF_FROM_NUMBER,
    CONF_PHRASE,
    CONF_PHRASE_EVENTS,
    CONF_PHRASES,
    DOMAIN,
    FROM_NUMBER_PATTERN,
    FROM_NUMBER_REPLACER,
)

_LOGGER = logging.getLogger(__name__)

EVENTS_KEY = "events"
PHRASES_KEY = "phrases"
SELECTION_KEY = "selection"

STEP_LIST_EVENTS = "list_events"
STEP_LIST_PHRASES = "list_phrases"
STEP_EDIT_EVENT = "edit_event"
STEP_EDIT_PHRASE = "edit_phrase"
STEP_SAVE = "save"
STEP_EXIT = "exit"

ACTION_ADD = "add"
ACTION_EDIT = "edit"
ACTION_SAVE = "save"
ACTION_CANCEL = "cancel"
ACTION_MENU = "menu"
ACTION_REMOVE = "remove"
ACTION_BACK = "back"
ACTION_EVENTS = "events"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_FROM_NUMBER): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.TEL,
                autocomplete="tel",
                multiline=False,
            )
        )
    }
)

OPTIONS_SCHEMA = vol.Schema(
    vol.All(
        cv.ensure_list,
        [
            vol.Schema(
                {
                    vol.Required(CONF_PHRASES): vol.All(cv.ensure_list, [cv.string]),
                    vol.Required(CONF_EVENT): cv.string,
                }
            ),
        ],
    )
)


def _pop_sys_keys(user_input: dict[str, Any] | None) -> SystemValues:
    """Pop the system keys out of the user input."""
    if user_input is None:
        return SystemValues()
    return SystemValues(
        event=user_input.pop(SYS_EVENT, None),
        event_index=user_input.pop(SYS_EVENT_INDEX, None),
        phrase=user_input.pop(SYS_PHRASE, None),
        phrase_index=user_input.pop(SYS_PHRASE_INDEX, None),
        user_input=user_input,
    )


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Configuratio nflow for twilio_call_live."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry[Any]) -> "OptionsFlowHandler":
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        return await self.async_step_init(user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial configuration flow step."""
        _errors = {}

        if user_input is not None:
            from_number = user_input.get(CONF_FROM_NUMBER, None)
            if from_number is not None:
                from_number = re.sub(FROM_NUMBER_REPLACER, "", from_number)
                if not FROM_NUMBER_PATTERN.match(from_number):
                    _errors[CONF_FROM_NUMBER] = "invalid_from_number"

            return self.async_create_entry(
                title=DOMAIN,
                data={CONF_FROM_NUMBER: from_number},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_FROM_NUMBER,
                            default=(user_input or {}).get(CONF_FROM_NUMBER, None),
                        ): str,
                    }
                ),
                user_input,
            ),
            errors=_errors,
        )


class OptionsFlowHandler(OptionsFlowWithConfigEntry):

    def __init__(self, config_entry: ConfigEntry[Any]) -> None:
        super().__init__(config_entry)
        _LOGGER.info("Starting options flow")
        _LOGGER.info(json.dumps({"data": {k: v for k, v in config_entry.data.items()}}))
        _LOGGER.info(
            json.dumps({"options": {k: v for k, v in config_entry.options.items()}})
        )
        self._event_phrases = EventPhrasesList(
            config_entry.options.get(CONF_PHRASE_EVENTS, [])
        )
        self.values = SystemValues()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user initiated options configuration."""
        _LOGGER.info("Step: user")
        return await self.async_step_init(user_input)

    async def async_step_list_events(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle listing events."""
        _LOGGER.info("Step: %s %s", STEP_LIST_EVENTS, json.dumps(user_input or "None"))
        _errors = {}
        self.values = SystemValues()
        if user_input is not None:
            action = user_input.pop(CONF_ACTION, None)
            selected_index = user_input.pop(EVENTS_KEY, None)

            if action is None or action == ACTION_MENU:
                return await self.async_step_menu()
            elif action == ACTION_ADD:
                return await self.async_step_edit_event()
            elif action == ACTION_BACK:
                return await self.async_step_menu()
            elif action == ACTION_EDIT:
                if selected_index is None:
                    _errors[EVENTS_KEY] = "no_event_selected"
                else:
                    selected_index = int(selected_index)
                    self.values.event = self._event_phrases[selected_index].event
                    self.values.event_index = selected_index
                    return await self.async_step_edit_event()
            elif action == ACTION_REMOVE:
                if selected_index is None:
                    _errors[EVENTS_KEY] = "no_event_selected"
                else:
                    selected_index = int(selected_index)
                    self._event_phrases.remove(self._event_phrases[selected_index])
                    if len(self._event_phrases) == 0:
                        return await self.async_step_menu()
                    else:
                        return await self.async_step_list_events()
        options = []
        options.append(SelectOptionDict(label="Add Event", value=ACTION_ADD))
        options.append(SelectOptionDict(label="Edit Event", value=ACTION_EDIT))
        options.append(SelectOptionDict(label="Delete Event", value=ACTION_REMOVE))
        options.append(SelectOptionDict(label="Menu", value=ACTION_MENU))

        return self.async_show_form(
            step_id=STEP_LIST_EVENTS,
            data_schema=vol.Schema(
                {
                    vol.Optional(EVENTS_KEY): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=ep.event, value=str(idx))  # type: ignore
                                for idx, ep in enumerate(self._event_phrases)
                            ],  # type: ignore
                            mode=SelectSelectorMode.LIST,
                            multiple=False,
                        )
                    ),
                    vol.Required(CONF_ACTION): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            multiple=False,
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_list_phrases(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle listing phrases."""
        _LOGGER.info(
            "Step: %s, %s", STEP_LIST_PHRASES, json.dumps(user_input or "None")
        )
        if self.values.event_index is None:
            return await self.async_step_list_events()
        self.values.phrase = None
        self.values.phrase_index = None
        _errors = {}
        if user_input is not None:
            action = user_input.pop(CONF_ACTION, None)
            selected_index = user_input.pop(PHRASES_KEY, None)

            if action is None or action == ACTION_MENU:
                return await self.async_step_menu()
            elif action == ACTION_BACK:
                return await self.async_step_edit_event()
            elif action == ACTION_EVENTS:
                self.values.event = None
                self.values.event_index = None
                return await self.async_step_list_events()
            elif action == ACTION_ADD:
                return await self.async_step_edit_phrase()
            elif action == ACTION_BACK:
                return await self.async_step_list_events()
            elif action == ACTION_EDIT:
                if selected_index is None:
                    _errors[PHRASES_KEY] = "no_event_selected"
                else:
                    selected_index = int(selected_index)
                    self.values.phrase = self._event_phrases[
                        self.values.event_index
                    ].get_pattern(selected_index)
                    self.values.phrase_index = selected_index
                    return await self.async_step_edit_phrase()
            elif action == ACTION_REMOVE:
                if selected_index is None:
                    _errors[PHRASES_KEY] = "no_event_selected"
                else:
                    selected_index = int(selected_index)
                    self._event_phrases.remove(self._event_phrases[selected_index])
                    if len(self._event_phrases) == 0:
                        self.values = SystemValues()
                        return await self.async_step_list_events()
                    else:
                        self.values.phrase = None
                        self.values.phrase_index = None
                        return await self.async_step_list_phrases()
        options = []
        options.append(SelectOptionDict(label="Add Phrase", value=ACTION_ADD))
        options.append(SelectOptionDict(label="Edit Phrase", value=ACTION_EDIT))
        options.append(SelectOptionDict(label="Delete Phrase", value=ACTION_REMOVE))
        options.append(SelectOptionDict(label="Back", value=ACTION_BACK))
        options.append(SelectOptionDict(label="Events", value=ACTION_EVENTS))
        options.append(SelectOptionDict(label="Menu", value=ACTION_MENU))

        return self.async_show_form(
            step_id=STEP_LIST_EVENTS,
            data_schema=vol.Schema(
                {
                    vol.Optional(PHRASES_KEY): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=phrase, value=str(idx))  # type: ignore
                                for idx, phrase in enumerate(
                                    self._event_phrases[
                                        self.values.event_index
                                    ].patterns
                                )
                            ],  # type: ignore
                            mode=SelectSelectorMode.LIST,
                            multiple=False,
                        )
                    ),
                    vol.Required(CONF_ACTION): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            multiple=False,
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_edit_event(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        step_id = STEP_EDIT_EVENT
        _LOGGER.info("Step: %s", step_id)
        self.values.phrase = None
        self.values.phrase_index = None
        _errors = {}
        if user_input is not None:
            action = user_input.pop(CONF_ACTION, None)
            event = user_input.pop(CONF_EVENT, None)
            if action is None or action == ACTION_MENU:
                return await self.async_step_menu()
            elif action == ACTION_BACK:
                self.values = SystemValues()
                return await self.async_step_list_events()
            if event is None:
                _errors[CONF_EVENT] = "missing_event"
            else:
                try:
                    if self.values.event_index is None:
                        self._event_phrases.append(
                            EventPhrases(event=event, phrases=[])
                        )
                        self.values.event = event
                        self.values.event_index = len(self._event_phrases) - 1
                    else:
                        self._event_phrases[self.values.event_index].event = event
                        self.values.event = event
                    _LOGGER.info(
                        "Edit EventPhrase: event %s, %d, phrases %s",
                        self.values.event,
                        self.values.event_index,
                        [
                            ep
                            for ep in self._event_phrases[
                                self.values.event_index or -1
                            ].phrases
                        ],
                    )
                    if action == ACTION_ADD:
                        self.values.event = None
                        self.values.event_index = None
                        _LOGGER.info("Added, opening another event")
                        return await self.async_step_edit_event()
                    elif len(self._event_phrases[self.values.event_index].phrases) > 0:
                        return await self.async_step_list_phrases()
                    else:
                        return await self.async_step_edit_phrase()
                except Exception as err:
                    _LOGGER.error("Unexpected error parsing event: %s", err)
                    _errors[CONF_EVENT] = "invalid_event"

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_EVENT): TextSelector(
                            TextSelectorConfig(
                                type=TextSelectorType.TEXT, multiline=False
                            )
                        ),
                        vol.Required(CONF_ACTION): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    SelectOptionDict(
                                        label="Add Another", value=ACTION_ADD
                                    ),
                                    SelectOptionDict(
                                        label="Save & Open Phrases", value=ACTION_SAVE
                                    ),
                                    SelectOptionDict(label="Back", value=ACTION_BACK),
                                    SelectOptionDict(label="Menu", value=ACTION_MENU),
                                ],
                                mode=SelectSelectorMode.LIST,
                                multiple=False,
                                custom_value=False,
                            )
                        ),
                    }
                ),
                {CONF_EVENT: (user_input or {}).get(CONF_EVENT, self.values.event)},
            ),
            errors=_errors,
        )

    async def async_step_edit_phrase(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        step_id = STEP_EDIT_PHRASE
        _LOGGER.info("Step: %s", step_id)
        _errors = {}
        if user_input is not None:
            action = user_input.pop(CONF_ACTION, None)
            phrase = user_input.pop(CONF_PHRASE, None)
            if action is None or action == ACTION_MENU:
                return await self.async_step_menu()
            elif action == ACTION_CANCEL:
                self.values.phrase = None
                self.values.phrase_index = None
                return await self.async_step_list_phrases()
            if phrase is None:
                _errors[CONF_PHRASE] = "missing_phrase"
            else:
                try:
                    if self.values.phrase_index is None:
                        self._event_phrases[
                            self.values.event_index or -1
                        ].phrases.append(phrase)
                        self.values.phrase = phrase
                        self.values.phrase_index = len(
                            self._event_phrases[self.values.event_index or -1].phrases
                            or []
                        )
                    else:
                        self._event_phrases[self.values.event_index or -1].phrases[
                            self.values.phrase_index
                        ] = phrase
                        self.values.phrase = phrase
                    _LOGGER.info(
                        "Edit Phrase: event %s, phrase %s",
                        self.values.event,
                        self.values.phrase,
                    )
                    self.values.phrase = None
                    self.values.phrase_index = None
                    if action == ACTION_ADD:
                        return await self.async_step_edit_phrase()
                    else:
                        return await self.async_step_edit_event()
                except Exception as err:
                    _LOGGER.error("Unexpected error parsing phrase: %s", err)
                    _errors[CONF_PHRASE] = "invalid_phrase"

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_PHRASE): TextSelector(
                            TextSelectorConfig(
                                type=TextSelectorType.TEXT, multiline=False
                            )
                        ),
                        vol.Required(CONF_ACTION): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    SelectOptionDict(
                                        label="Add Another", value=ACTION_ADD
                                    ),
                                    SelectOptionDict(
                                        label="Save & Open Event", value=ACTION_SAVE
                                    ),
                                    SelectOptionDict(
                                        label="Cancel Changes", value=ACTION_CANCEL
                                    ),
                                    SelectOptionDict(label="Menu", value=ACTION_MENU),
                                ],
                                mode=SelectSelectorMode.LIST,
                                multiple=False,
                                custom_value=False,
                            )
                        ),
                    }
                ),
                {CONF_PHRASE: (user_input or {}).get(CONF_PHRASE, self.values.phrase)},
            ),
            errors=_errors,
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage twilio call live options."""
        _LOGGER.info("Step: init")
        return await self.async_step_menu(user_input)

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the configuration menu to the user."""
        _LOGGER.info("Step: menu")
        self.values = SystemValues()
        return self.async_show_menu(
            step_id="menu",
            menu_options={
                STEP_LIST_EVENTS: "Edit Events",
                STEP_SAVE: "Save Changes and Close",
                STEP_EXIT: "Close Without Save",
            },
        )

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save and close the config flow."""
        return self.async_create_entry(
            title=DOMAIN,
            data={
                **self.config_entry.data,
                CONF_PHRASE_EVENTS: [event.to_dict() for event in self._event_phrases],
            },
        )

    async def async_step_exit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Exit without saving."""
        return self.async_abort(reason="user_aborted")
