<p align="center">
  <a href="https://awesome-mlss.com/">
    <img src="https://awesome-mlss.com/static/img/favicon.png" width="320" alt="Awesome MLSS logo">
  </a>
</p>

<p align="center">
  <strong>
    Awesome MLSS
  </strong>
  <br>
    A community project to keep track of deadlines for Machine Learning Summer Schools (MLSS) around the world
</p>

<p align="center">
  <a href="https://x.com/awesomeMLSS"><img alt="X (formerly Twitter) Follow" src="https://img.shields.io/twitter/follow/awesomeMLSS"></a>
  <a href="https://github.com/sshkhr/awesome-mlss/pulse" alt="Activity"><img src="https://img.shields.io/github/commit-activity/m/sshkhr/awesome-mlss"/></a>  
  <a href="https://github.com/sshkhr/awesome-mlss"><img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen" alt="Contributions Welcome"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <img alt="Netlify" src="https://img.shields.io/netlify/2839ba31-3fab-4b5b-984a-995e437d79ed?logoColor=red">
  <a href="https://github.com/sshkhr/awesome-mlss/stargazers"><img src="https://img.shields.io/github/stars/sshkhr/awesome-mlss" alt="GitHub Stars"></a>
</p>

[awesome-mlss.com](https://awesome-mlss.com/) is a community tool which serves as a central repository for registration deadlines at summer schools in machine learning and other closely related fields.

## 2025 Summer Schools
Title|Topics|Place|Deadline|Dates|Details
-----|------|-----|--------|-----|-------
International Artificial Intelligence Summer School|Machine Learning|Grosseto, Italy|Mar 23, 2025|Sep 21 - Sep 25, 2025|[Details](https://awesome-mlss.com/summerschool/IAISS25)
Bumblekite Machine Learning Summer School in Health, care and biosciences|Machine Learning, ML for Health, ML for Biology|Zürich, Switzerland|Mar 09, 2025|Jun 22 - Jun 28, 2025|[Details](https://awesome-mlss.com/summerschool/bumblekite25)
Advanced Course on Data Science & Machine Learning|Machine Learning|Grosseto, Italy|Feb 23, 2025|Jun 09 - Jun 13, 2025|[Details](https://awesome-mlss.com/summerschool/acdl25)
Summer School in Responsible AI and Human Rights|Responsible AI|Montreal, Canada|Jan 06, 2025|May 26 - May 30, 2025|[Details](https://awesome-mlss.com/summerschool/ssraihr25)
Winter School: Next Generation AI and Economic Applications|Generative AI, AI and Economics|UM6P Ben Guerir Campus, Morocco|Jan 30, 2025|Feb 24 - Feb 25, 2025|[Details](https://awesome-mlss.com/summerschool/wsngaiea25)
UM6P Winter School on Data Economics|ML Theory, AI and Economics|UM6P Rabat Campus, Morocco|Dec 08, 2024|Jan 20 - Jan 24, 2025|[Details](https://awesome-mlss.com/summerschool/wsde25)
Winter School on Emerging Technologies|Machine Learning, Robotics|Mesa, AZ|Oct 07, 2024|Jan 03 - Jan 10, 2025|[Details](https://awesome-mlss.com/summerschool/ASUWinterSchool25)

## Contributing

Contributions are very welcome!

To add or update a new summer school deadline:
- Fork the repository
- Optional: create a new branch with the name of the summer school
- Update `site/_data/summerschools.yml`
- Make sure it has the `title`, `year`, `id`, `link`, `deadline`, `timezone`, `date`, `place`, `sub` attributes
    + Please use one of the timezone string mentioned in [timezones](timezones.md).
    + Please use one of the subcategory mentioned in [topics](topics.md). Use the value of the `sub` attribute to specify the subcategory.
- Optionally add a `note` in case there is important information to convey
- Example:
    ```yaml
    - title: BestMLSS # (required❗)
      year: 2024 # (required❗)
      id: bestmlss24  # title as lower case + last two digits of year # (required❗)
      full_name: Best Machine Learning Summer School # full school name # (required❗)
      link: link-to-website.com # (required❗)
      deadline: YYYY-MM-DD HH:SS # (required❗)
      timezone: Asia/Seoul # (required❗)
      place: Incheon, South Korea # (required❗)
      date: September 18 - September 22, 2024 # (required❗)
      start: YYYY-MM-DD # (required❗)
      end: YYYY-MM-DD # (required❗)
      sub: Ml, NLP #(at least 1 required❗)
      note: Any important notes about the school # (optional🤙)
    ```
- Send a pull request

## Acknowledgements

The awesome-mlss website was built upon the amazing work done by:

- [https://aideadlin.es/][1] by [@abhshkdz](https://twitter.com/abhshkdz) and [Papers With Code](https://paperswithcode.com/)
- [pythondeadlin.es][2] by [@jesperdramsch](https://dramsch.net/)

## License

This project is licensed under [MIT][1].

It uses:

- [IcoMoon Icons](https://icomoon.io/#icons-icomoon): [GPL](http://www.gnu.org/licenses/gpl.html) / [CC BY4.0](http://creativecommons.org/licenses/by/4.0/)


[1]: http://aideadlin.es/
[2]: https://pythondeadlin.es/