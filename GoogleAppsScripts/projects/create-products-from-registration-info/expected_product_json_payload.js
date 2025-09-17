/*
{
    sportName: string [enum - 'Dodgeball' or 'Kickball' or 'Bowling' or 'Pickleball']
    division: string [either 'WTNB+' or 'Open']
    season: 'string' [either 'Fall', 'Winter', 'Summer', 'Spring']
    year: string [YYYY]
    dayOfPlay: string [enum - day of week capitalized]
    location: string [enum, any of the following:
                'Elliott Center (26th St & 9th Ave)',
                'PS3 Charrette School (Grove St & Hudson St)',
                'Village Community School (10th St & Greenwich St)',
                'Hartley House (46th St & 9th Ave)',
                'Dewitt Clinton Park (52nd St & 11th Ave)',
                'Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)',
                'Chelsea Park (27th St & 9th Ave)',
                'Gotham Pickleball (46th and Vernon in LIC)',
                'John Jay College (59th and 10th)',
                'Pickle1 (7 Hanover Square in LIC)',
                'Frames Bowling Lounge (40th St and 9th Ave)',
                'Bowlero Chelsea Piers (60 Chelsea Piers)'
                ]
    optionalLeagueInfo?: {
        sportSubCategory?: string [enum - 'Big Ball' or 'Small Ball' or 'Foam']
        socialOrAdvanced?: string [enum - 'Social' or 'Advanced' or 'Mixed Social/Advanced' or 'Competitive/Advanced' or 'Intermediate/Advanced']
        types?: [stringArray] [enum - 'Draft' or 'Randomized Teams' or 'Buddy Sign-up' or 'Sign up with a newbie (randomized otherwise)']
    }
    importantDates: {
        newPlayerOrientationDateTime?: Date | string
        scoutNightDateTime?: Date | string
        openingPartyDate?: Date | string
        seasonStartDate: Date
        seasonEndDate: Date
        offDates?: Date[]
        rainDate?: Date | string
        closingPartyDate?: Date | string
        vetRegistrationStartDateTime?: Date
        earlyRegistrationStartDateTime: Date
        openRegistrationStartDateTime: Date

    }
    leagueStartTime: string
    leagueEndTime: string
    alternativeStartTime?: String
    alternativeEndTime?: String
    inventoryInfo: {
        price: number
        totalInventory: number
        numberVetSpotsToReleaseAtGoLive: number
    }
}

*/
