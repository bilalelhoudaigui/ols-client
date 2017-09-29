# -*- coding: utf-8 -*-

import logging
import time

import requests

from .constants import BASE_URL

__all__ = [
    'OlsClient'
]

log = logging.getLogger(__name__)


def get_ols_search(name):
    """Performs a search with the Ontology Lookup Service"""
    res = requests.get(OLS_MACHINE_SEARCH_FMT, params={'q': name})
    return res.json()


def iterate_response_terms(response):
    """Iterates over the terms in the given response"""
    embedded = response['_embedded']

    terms = embedded['terms']

    for term in terms:
        yield term


class OlsClient:
    """Wraps the functions to query the Ontology Lookup Service"""

    def __init__(self, ols_base=None):
        """
        :param ols_base: An optional, custom URL for the OLS RESTful API.
        """
        self.base = (ols_base if ols_base is not None else BASE_URL).rstrip('/')

        self.ontology_terms_fmt = self.base + '/ontologies/{}/terms'
        self.ontology_metadata_fmt = self.base + '/ontologies/{}'

        self.ontology_suggest = self.base + '/suggest'

        self.ontology_search = self.base + '/search'

    def search(self, name):
        """Searches the OLS with the given term

        :param str name:
        :return: dict
        """
        response = requests.get(self.ontology_search, params={'q': name})
        return response.json()

    def suggest(self, name, ontology=None):
        """Suggest terms from an optional list of ontologies

        :param str name:
        :param list[str] ontology:
        :rtype: dict

        .. seealso:: https://www.ebi.ac.uk/ols/docs/api#_suggest_term
        """
        params = {'q': name}
        if ontology:
            params['ontology'] = ','.join(ontology)
        response = requests.get(self.ontology_suggest, params=params)
        return response.json()

    def iterate_ontology_terms(self, ontology_name, size=500):
        """Iterates over all terms, lazily with paging

        :param str ontology_name: The name of the ontology
        :param int size: The size of each page. EBI says 500 is the maximum size
        """
        if size > 500:
            raise ValueError('Maximum size is 500. Given: {}'.format(size))

        url = self.ontology_terms_fmt.format(ontology_name)

        t = time.time()
        response = requests.get(url, params={'size': size}).json()
        links = response['_links']

        for x in iterate_response_terms(response):
            yield x

        t = time.time() - t

        log.info(
            'Page %s/%s done in %.2f seconds',
            response['page']['number'],
            response['page']['totalPages'],
            t
        )

        log.info('Estimated time until done: %.2f', t * response['page']['totalPages'] / 60)

        while 'next' in links:
            t = time.time()
            response = requests.get(links['next']['href'], params={'size': size}).json()
            links = response['_links']

            for x in iterate_response_terms(response):
                yield x

            log.info(
                'Page %s/%s done in %.2f seconds',
                response['page']['number'],
                response['page']['totalPages'],
                time.time() - t
            )

    def get_labels(self, ontology_name):
        """Iterates over the labels of terms in the ontology

        :param str ontology_name: The name of the ontology
        :rtype: iter[str]
        """
        log.info('Getting data from %s', ontology_name)
        for term in self.iterate_ontology_terms(ontology_name):
            yield term['label']

    def get_metadata(self, ontology_name):
        """Gets the metadata for a given ontology

        :param str ontology_name: The name of the ontology
        :return: The dictionary representing the JSON from the OLS
        :rtype: dict
        """
        url = self.ontology_metadata_fmt.format(ontology_name)
        response = requests.get(url).json()
        return response

    def get_description(self, ontology_name):
        """Gets the description of a given ontology

        :param str ontology_name: The name of the ontology
        :rtype: str
        """
        response = self.get_metadata(ontology_name)

        return response['config'].get('description')