"""Config-flow tests for the samsungwam `fixes/easy-wins` branch.

Covers the connect-error behavioural fix on the ``user`` step:

  * connect-error path -> re-show form (this branch) vs abort (master)

This branch is off ``master`` and has NO custom port field, so the form
is submitted with the host ONLY (adding a CONF_PORT key would fail with
"extra keys not allowed").

The pywam ``Speaker`` used inside the flow is fully mocked, so no real
speaker/network is touched.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.samsungwam.const import DOMAIN

SPEAKER_MODULE = "custom_components.samsungwam.config_flow.Speaker"

TEST_HOST = "192.168.1.55"
TEST_NAME = "Living Room Speaker"
TEST_MODEL = "SPK-WAM550"
TEST_ID = "AABBCCDDEEFF"


def make_speaker(*, name=TEST_NAME, model=TEST_MODEL, speaker_id=TEST_ID, fail=False):
    """Return a mock that stands in for ``pywam.speaker.Speaker(host)``.

    The flow uses ``async with Speaker(host) as speaker``, so the object
    returned by calling ``Speaker(...)`` must be an async context manager whose
    ``__aenter__`` yields the mocked speaker.
    """
    speaker = MagicMock()
    speaker.get_name = AsyncMock(return_value=name)
    speaker.get_model = AsyncMock(return_value=model)
    speaker.get_speaker_id = AsyncMock(return_value=speaker_id)
    speaker.update = AsyncMock(
        side_effect=Exception("cannot connect") if fail else None
    )

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=speaker)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# user error path -> re-show form with errors["base"] == "cannot_connect"
#     (this branch). On master the flow ABORTS instead, so this FAILS there.
#
# NB: host-ONLY submission -- this branch has no port field.
# ---------------------------------------------------------------------------
async def test_user_connect_error_reshows_form(hass: HomeAssistant) -> None:
    """A connect/update failure must keep the user on the form, not abort."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(SPEAKER_MODULE, return_value=make_speaker(fail=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )

    # this branch: form is re-shown with a recoverable error.
    # master: async_validate_device returns self.async_abort(...) -> ABORT.
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}
