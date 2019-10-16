# wikimedia_cats.py
# gets cat-related stuff from wikipedia.

import aiohttp
from typing import Dict
import random
import io


class wikicats:
    def __init__(self):
        pass

    async def async_init(self, image_id=None):
        self.cat_list = await self._get_cat_breeds()
        self.breed = self._get_random_cat_breed()
        self.images_list = await self._get_random_cat_images()
        self.info = await self._get_random_cat_image(image_id)

    async def _get_wikimedia_query_api(
            self, cmpageid: int, cmnamespace: int) -> Dict[str, str]:
        """ Gets full list of category members based on numeric cmpageid
        input. Requests for maximum number of entries. Returns JSON list
        of entries. """
        # cmnamespace 14 is just for categories only, while cmnamespace 6
        # is for files.
        params = {"action": "query", "list": "categorymembers",
                  "format": "json", "cmpageid": cmpageid,
                  "cmnamespace": cmnamespace, "cmlimit": "max"}
        url = "https://commons.wikimedia.org/w/api.php"
        async with aiohttp.ClientSession() as session:
            async_res = await session.get(url, params=params, timeout=10)
        # The default return also returns batchcomplete information.
        # We don't care, so we only return the category's members.
        res = await async_res.json()
        return res['query']['categorymembers']

    async def _get_wikimedia_imageinfo_api(self, pageid):
        """ Retrieves image information from a provided page ID. Returns a
        JSON list of credited user, direct URL, and a link to further
        information on the image. """
        params = {"action": "query", "prop": "imageinfo", "format": "json",
                  "iiprop": "user|url|extmetadata", "pageids": pageid,
                  "iiurlwidth": "720"}
        url = "https://commons.wikimedia.org/w/api.php"
        async with aiohttp.ClientSession() as session:
            r = await session.get(url, params=params, timeout=10)
        try:
            res = await r.json()
            image_info = (res['query']['pages']
                          [str(pageid)]['imageinfo'][0])
            image_info['imageid'] = pageid
        except KeyError:
            raise KeyError('Page ID {} not found.'.format(pageid))
        return image_info

    async def _get_cat_breeds(self):
        """ Gets full list of cat breeds. Returns JSON list of cat breeds. """
        # 37973 is the category for cat breeds on Wikimedia.
        cat_list = await self._get_wikimedia_query_api(37973, 14)
        return cat_list

    def _get_random_cat_breed(self):
        """ Takes a random cat breed from a list of cats. Returns JSON info
        of cat breed. """
        breed = random.choice(self.cat_list)
        return breed

    async def _get_random_cat_images(self):
        """ Gets a list of cat images based on the breed. Returns JSON
        list of cat image information. """
        breed_id = self.breed['pageid']
        images_list = await self._get_wikimedia_query_api(breed_id, 6)
        # No empty images list.
        while not images_list:
            cat_list = await self._get_wikimedia_query_api(
                breed_id['pageid'], 14)
            if not cat_list:
                raise IndexError(f'No cat images found for {breed_id}.')
            breed_id = random.choice(cat_list)['pageid']
            images_list = await self._get_wikimedia_query_api(breed_id, 6)
        return images_list

    async def _get_random_cat_image(self, image_id=None):
        """ Gets a random image from a selected breed on Wikimedia Commons.
        Returns JSON information about an image, including URL and copyright
        information. """
        if image_id is None:
            image_id = random.choice(self.images_list)['pageid']
        catte = await self._get_wikimedia_imageinfo_api(image_id)
        return catte

    async def get_picture(self) -> io.BytesIO:
        '''
        Downloads a picture.
        '''
        async with aiohttp.ClientSession() as session:
            resp = await session.get(self.info['thumburl'], timeout=10)
            if resp.status >= 400:
                raise aiohttp.ClientResponseError((), resp.status)
            output = io.BytesIO(await resp.read())
            return output
