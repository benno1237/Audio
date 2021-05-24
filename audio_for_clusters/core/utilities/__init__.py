from ..cog_utils import CompositeMetaClass
from .equalizer import EqualizerUtilities
from .formatting import FormattingUtilities
from .local_tracks import LocalTrackUtilities
from .miscellaneous import MiscellaneousUtilities
from .parsers import ParsingUtilities
from .player import PlayerUtilities
from .playlists import PlaylistUtilities
from .queue import QueueUtilities
from .validation import ValidationUtilities
from .setting_cache import SettingCacheManager as SettingCacheManager


class Utilities(
    EqualizerUtilities,
    FormattingUtilities,
    LocalTrackUtilities,
    MiscellaneousUtilities,
    PlayerUtilities,
    PlaylistUtilities,
    QueueUtilities,
    ValidationUtilities,
    ParsingUtilities,
    metaclass=CompositeMetaClass,
):
    """Class joining all utility subclasses"""