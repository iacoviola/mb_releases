import os
import logging

from datetime import datetime as dt
from time import time

from db.music_db import MusicDB as MDB

logger = logging.getLogger(__name__)

class IcalBuilder:
    '''
    Class to generate an iCal file for new releases

    Attributes:
        __db (MDB): The database object
        __template (str): The template of the iCal file
        __prepend (str): The prolog of the iCal file
        __append (str): The epilog of the iCal file
        __ical (str): The iCal file
    '''

    def __init__(self, db: MDB, template_path: str):
        self.__db = db
        self.__template = open(template_path).read()

        self.__prepend = 'BEGIN:VCALENDAR\nVERSION:2.0\nMETHOD:PUBLISH\nPRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'
        self.__append = 'END:VCALENDAR'
        self.__ical = self.__prepend

    def __db_to_ical(self, date: str) -> str:
        '''
        Converts a date from the database format to the iCal format

        Parameters:
            date (str): The date to convert

        Returns:
            str: The converted date
        '''
        
        return dt.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
        
    def build_ical(self, keep_types: list = []):
        '''
        Builds the iCal file

        Parameters:
            keep_types (list): The types of releases to select
        '''

        for event in self.__db.get_releasing(keep_types, add_cols=['last_updated']):
            
            logger.debug('Event: ' + str(event))

            r_id, r_mbid, a_id, r_title, r_date, r_prim_type, r_lastupd = event

            try:
                r_date = self.__db_to_ical(r_date)
            except ValueError:
                logger.error('Invalid date: ' + r_date + " for release: " + r_title)
                continue

            try:
                tstamp = dt.strptime(r_lastupd, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                tstamp = dt.strptime(r_lastupd, '%Y-%m-%dT%H:%M:%S.%f')

            tstamp = tstamp.strftime('%Y%m%dT%H%M%SZ')
            aname = self.__db.get_artist_name(a_id)
            t_other = self.__db.get_other_types(r_id)

            r_types = f"({', '.join(t_other)})" if t_other else r_prim_type

            entry = self.__template.format(r_title=r_title,
                                           a_name=aname,
                                           uid=r_mbid,
                                           tstamp=tstamp,
                                           r_date=r_date,
                                           categories=r_prim_type,
                                           type=r_types)
            
            logger.debug('Writing event: ' + entry)
            self.__ical += entry

        self.__ical += self.__append
            
    def save(self, file_name: str):
        '''
        Saves the iCal file to a file

        Parameters:
            file_name (str): The name of the file to save the iCal to
        '''

        with(open(file_name, 'w')) as file:
            file.write(self.__ical)

        time_now = time()
        os.utime(file_name, (time_now, time_now))

        logger.info('File saved: ' + file_name)