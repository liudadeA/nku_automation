from setuptools import setup
import os
from glob import glob

package_name = 'course_demo'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        (os.path.join('share', package_name, 'param'), glob('param/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zy',
    maintainer_email='zy@todo.todo',
    description='TurtleBot3 mapping and navigation demo for course',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'auto_explorer = course_demo.auto_explorer:main',
            'auto_navigator = course_demo.auto_navigator:main',
        ],
    },
)
