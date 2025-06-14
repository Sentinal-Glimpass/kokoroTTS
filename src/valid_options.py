# src/valid_options.py

# Based on the provided VOICES.md from Kokoro-82M
# This is a representative subset. In a production system, this might be loaded from a config file or a more complete list.

# The lang_code here refers to the 'short code' used in VOICES.md (e.g., 'a' for American English)
# which aligns with how voices are grouped, e.g. af_heart, hf_beta.
# The API will take this short lang_code for voice validation purposes.

VALID_LANG_VOICES = {
    "a": { # American English
        "voices": ["af_adele", "af_amy", "af_ann", "af_carl", "af_clara", "af_david", "af_derek", "af_elizabeth", "af_emma", "af_grace", "af_henry", "af_jack", "af_james", "af_jessica", "af_john", "af_katie", "af_kevin", "af_laura", "af_linda", "af_mark", "af_mary", "af_michael", "af_mike", "af_peter", "af_rachel", "af_richard", "af_robert", "af_sam", "af_sarah", "af_susan", "af_tom", "af_william", "am_austin", "am_ben", "am_brian", "am_chris", "am_daniel", "am_eric", "am_george", "am_jacob", "am_jason", "am_jeffrey", "am_joseph", "am_joshua", "am_justin", "am_keith", "am_kevin", "am_kyle", "am_larry", "am_matthew", "am_paul", "am_ryan", "am_scott", "am_sean", "am_shawn", "am_stephen", "am_steven", "am_timothy", "am_todd", "am_tyler", "am_victor", "af_heart", "af_star", "am_wave"]
    },
    "b": { # British English
        "voices": [
            "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
            "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
        ]
    },
    "j": { # Japanese
        "voices": ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"]
    },
    "z": { # Mandarin Chinese
        "voices": [
            "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
            "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang"
        ]
    },
    "e": { # Spanish
        "voices": ["ef_dora", "em_alex", "em_santa"]
    },
    "f": { # French
        "voices": ["ff_siwis"]
    },
    "h": { # Hindi
        "voices": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"]
    },
    "i": { # Italian
        "voices": ["if_sara", "im_nicola"]
    },
    "p": { # Brazilian Portuguese
        "voices": ["pf_dora", "pm_alex", "pm_santa"]
    }
}

# Speed validation parameters
MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

SUPPORTED_API_LANG_CODES = list(VALID_LANG_VOICES.keys())
